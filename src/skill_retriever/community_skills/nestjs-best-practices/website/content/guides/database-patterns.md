---
title: Database Patterns
description: Learn repository patterns, transactions, and database best practices with Prisma and TypeORM
difficulty: intermediate
category: architecture
estimatedTime: 20 min
order: 8
prerequisites:
  - module-architecture
  - dependency-injection
---

# Database Patterns

This guide covers essential database patterns for NestJS applications, including repository abstraction, transactions, and query optimization.

## Repository Pattern

The repository pattern abstracts database operations, making your code more testable and maintainable.

### Basic Repository with Prisma

```typescript
// users/users.repository.ts
import { Injectable } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';
import { User, Prisma } from '@prisma/client';

@Injectable()
export class UsersRepository {
  constructor(private prisma: PrismaService) {}

  async findById(id: string): Promise<User | null> {
    return this.prisma.user.findUnique({
      where: { id },
    });
  }

  async findByEmail(email: string): Promise<User | null> {
    return this.prisma.user.findUnique({
      where: { email },
    });
  }

  async findMany(params: {
    skip?: number;
    take?: number;
    where?: Prisma.UserWhereInput;
    orderBy?: Prisma.UserOrderByWithRelationInput;
  }): Promise<User[]> {
    const { skip, take, where, orderBy } = params;
    return this.prisma.user.findMany({
      skip,
      take,
      where,
      orderBy,
    });
  }

  async count(where?: Prisma.UserWhereInput): Promise<number> {
    return this.prisma.user.count({ where });
  }

  async create(data: Prisma.UserCreateInput): Promise<User> {
    return this.prisma.user.create({ data });
  }

  async update(id: string, data: Prisma.UserUpdateInput): Promise<User> {
    return this.prisma.user.update({
      where: { id },
      data,
    });
  }

  async delete(id: string): Promise<User> {
    return this.prisma.user.delete({
      where: { id },
    });
  }
}
```

### Using the Repository in Services

```typescript
// users/users.service.ts
import { Injectable, NotFoundException, ConflictException } from '@nestjs/common';
import { UsersRepository } from './users.repository';
import { CreateUserDto } from './dto/create-user.dto';
import { UpdateUserDto } from './dto/update-user.dto';
import { hashPassword } from '../common/utils/hash';

@Injectable()
export class UsersService {
  constructor(private usersRepository: UsersRepository) {}

  async findById(id: string) {
    const user = await this.usersRepository.findById(id);
    if (!user) {
      throw new NotFoundException(`User with id ${id} not found`);
    }
    return user;
  }

  async findAll(params: { page: number; limit: number; search?: string }) {
    const { page, limit, search } = params;
    const skip = (page - 1) * limit;

    const where = search
      ? {
          OR: [
            { name: { contains: search, mode: 'insensitive' as const } },
            { email: { contains: search, mode: 'insensitive' as const } },
          ],
        }
      : undefined;

    const [users, total] = await Promise.all([
      this.usersRepository.findMany({ skip, take: limit, where }),
      this.usersRepository.count(where),
    ]);

    return {
      data: users,
      meta: {
        total,
        page,
        limit,
        totalPages: Math.ceil(total / limit),
      },
    };
  }

  async create(dto: CreateUserDto) {
    const existingUser = await this.usersRepository.findByEmail(dto.email);
    if (existingUser) {
      throw new ConflictException('Email already registered');
    }

    const passwordHash = await hashPassword(dto.password);
    return this.usersRepository.create({
      ...dto,
      passwordHash,
    });
  }

  async update(id: string, dto: UpdateUserDto) {
    await this.findById(id); // Ensure user exists
    return this.usersRepository.update(id, dto);
  }
}
```

## Transaction Management

### Using Prisma Transactions

```typescript
// orders/orders.service.ts
import { Injectable } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';

@Injectable()
export class OrdersService {
  constructor(private prisma: PrismaService) {}

  async createOrder(userId: string, items: OrderItemDto[]) {
    return this.prisma.$transaction(async (tx) => {
      // 1. Verify stock availability
      for (const item of items) {
        const product = await tx.product.findUnique({
          where: { id: item.productId },
        });

        if (!product || product.stock < item.quantity) {
          throw new Error(`Insufficient stock for product ${item.productId}`);
        }
      }

      // 2. Create the order
      const order = await tx.order.create({
        data: {
          userId,
          status: 'pending',
          items: {
            create: items.map((item) => ({
              productId: item.productId,
              quantity: item.quantity,
              price: item.price,
            })),
          },
        },
        include: { items: true },
      });

      // 3. Update stock
      for (const item of items) {
        await tx.product.update({
          where: { id: item.productId },
          data: { stock: { decrement: item.quantity } },
        });
      }

      // 4. Create payment record
      await tx.payment.create({
        data: {
          orderId: order.id,
          amount: items.reduce((sum, i) => sum + i.price * i.quantity, 0),
          status: 'pending',
        },
      });

      return order;
    });
  }
}
```

### Interactive Transactions with Timeout

```typescript
// payments/payments.service.ts
import { Injectable } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';

@Injectable()
export class PaymentsService {
  constructor(private prisma: PrismaService) {}

  async processPayment(orderId: string, paymentDetails: PaymentDetails) {
    return this.prisma.$transaction(
      async (tx) => {
        // Lock the order row
        const order = await tx.order.findUnique({
          where: { id: orderId },
        });

        if (!order || order.status !== 'pending') {
          throw new Error('Order not available for payment');
        }

        // Process payment with external provider
        const paymentResult = await this.paymentGateway.charge(paymentDetails);

        // Update order status
        await tx.order.update({
          where: { id: orderId },
          data: { status: paymentResult.success ? 'paid' : 'payment_failed' },
        });

        // Update payment record
        await tx.payment.update({
          where: { orderId },
          data: {
            status: paymentResult.success ? 'completed' : 'failed',
            transactionId: paymentResult.transactionId,
          },
        });

        return paymentResult;
      },
      {
        maxWait: 5000, // Max time to acquire lock
        timeout: 30000, // Max transaction duration
      },
    );
  }
}
```

## Query Optimization

### Selecting Only Required Fields

```typescript
// users/users.repository.ts
async findByIdForProfile(id: string) {
  return this.prisma.user.findUnique({
    where: { id },
    select: {
      id: true,
      name: true,
      email: true,
      avatar: true,
      createdAt: true,
      // Exclude sensitive fields like passwordHash
    },
  });
}

async findByIdWithPosts(id: string) {
  return this.prisma.user.findUnique({
    where: { id },
    include: {
      posts: {
        select: {
          id: true,
          title: true,
          createdAt: true,
        },
        orderBy: { createdAt: 'desc' },
        take: 10,
      },
    },
  });
}
```

### Batch Operations

```typescript
// notifications/notifications.service.ts
async markAllAsRead(userId: string) {
  return this.prisma.notification.updateMany({
    where: {
      userId,
      readAt: null,
    },
    data: {
      readAt: new Date(),
    },
  });
}

async deleteOldNotifications(olderThan: Date) {
  return this.prisma.notification.deleteMany({
    where: {
      createdAt: { lt: olderThan },
      readAt: { not: null },
    },
  });
}
```

### Raw Queries for Complex Operations

```typescript
// analytics/analytics.service.ts
async getTopSellingProducts(startDate: Date, endDate: Date) {
  return this.prisma.$queryRaw`
    SELECT
      p.id,
      p.name,
      SUM(oi.quantity) as total_sold,
      SUM(oi.quantity * oi.price) as revenue
    FROM products p
    JOIN order_items oi ON p.id = oi.product_id
    JOIN orders o ON oi.order_id = o.id
    WHERE o.created_at BETWEEN ${startDate} AND ${endDate}
      AND o.status = 'completed'
    GROUP BY p.id, p.name
    ORDER BY total_sold DESC
    LIMIT 10
  `;
}
```

## Soft Deletes

### Implementing Soft Deletes

```typescript
// prisma/schema.prisma
model User {
  id        String    @id @default(cuid())
  email     String    @unique
  name      String
  deletedAt DateTime? // Soft delete marker
  // ...
}

// users/users.repository.ts
@Injectable()
export class UsersRepository {
  constructor(private prisma: PrismaService) {}

  // Always filter out soft-deleted records by default
  async findById(id: string) {
    return this.prisma.user.findFirst({
      where: {
        id,
        deletedAt: null,
      },
    });
  }

  async findMany(params: FindManyParams) {
    return this.prisma.user.findMany({
      ...params,
      where: {
        ...params.where,
        deletedAt: null, // Exclude soft-deleted
      },
    });
  }

  // Soft delete
  async softDelete(id: string) {
    return this.prisma.user.update({
      where: { id },
      data: { deletedAt: new Date() },
    });
  }

  // Restore soft-deleted record
  async restore(id: string) {
    return this.prisma.user.update({
      where: { id },
      data: { deletedAt: null },
    });
  }

  // Include soft-deleted records (for admin views)
  async findManyWithDeleted(params: FindManyParams) {
    return this.prisma.user.findMany(params);
  }

  // Permanent delete
  async hardDelete(id: string) {
    return this.prisma.user.delete({
      where: { id },
    });
  }
}
```

## Database Connection Management

### Prisma Service Setup

```typescript
// prisma/prisma.service.ts
import { Injectable, OnModuleInit, OnModuleDestroy } from '@nestjs/common';
import { PrismaClient } from '@prisma/client';

@Injectable()
export class PrismaService
  extends PrismaClient
  implements OnModuleInit, OnModuleDestroy
{
  constructor() {
    super({
      log: process.env.NODE_ENV === 'development'
        ? ['query', 'info', 'warn', 'error']
        : ['error'],
    });
  }

  async onModuleInit() {
    await this.$connect();
  }

  async onModuleDestroy() {
    await this.$disconnect();
  }

  // Helper for cleaning database in tests
  async cleanDatabase() {
    if (process.env.NODE_ENV !== 'test') {
      throw new Error('cleanDatabase only allowed in test environment');
    }

    const models = Reflect.ownKeys(this).filter(
      (key) => typeof key === 'string' && !key.startsWith('_') && !key.startsWith('$'),
    );

    return Promise.all(
      models.map((modelKey) => (this as any)[modelKey]?.deleteMany?.()),
    );
  }
}
```

### Health Check

```typescript
// health/health.controller.ts
import { Controller, Get } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';

@Controller('health')
export class HealthController {
  constructor(private prisma: PrismaService) {}

  @Get()
  async check() {
    try {
      await this.prisma.$queryRaw`SELECT 1`;
      return {
        status: 'healthy',
        database: 'connected',
        timestamp: new Date().toISOString(),
      };
    } catch (error) {
      return {
        status: 'unhealthy',
        database: 'disconnected',
        error: error.message,
        timestamp: new Date().toISOString(),
      };
    }
  }
}
```

## Pagination Helper

```typescript
// common/utils/pagination.ts
export interface PaginationParams {
  page: number;
  limit: number;
}

export interface PaginatedResult<T> {
  data: T[];
  meta: {
    total: number;
    page: number;
    limit: number;
    totalPages: number;
    hasNextPage: boolean;
    hasPrevPage: boolean;
  };
}

export function createPaginatedResult<T>(
  data: T[],
  total: number,
  params: PaginationParams,
): PaginatedResult<T> {
  const { page, limit } = params;
  const totalPages = Math.ceil(total / limit);

  return {
    data,
    meta: {
      total,
      page,
      limit,
      totalPages,
      hasNextPage: page < totalPages,
      hasPrevPage: page > 1,
    },
  };
}
```

## Summary

- Use the **repository pattern** to abstract database operations
- Handle **transactions** for operations that must succeed or fail together
- **Optimize queries** by selecting only needed fields
- Implement **soft deletes** for recoverable data
- Use **batch operations** for bulk updates
- Properly manage **database connections** with lifecycle hooks
- Create **reusable pagination** helpers
