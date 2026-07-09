---
title: Testing NestJS Applications
description: Write reliable unit tests, integration tests, and e2e tests for your NestJS application
difficulty: intermediate
category: patterns
estimatedTime: 25 min
order: 6
prerequisites:
  - dependency-injection
---

# Testing NestJS Applications

Testing is essential for building reliable NestJS applications. This guide covers unit testing, integration testing, and end-to-end testing patterns.

## Setting Up the Test Environment

NestJS uses Jest by default. Your project should already have the testing dependencies:

```bash
npm install --save-dev @nestjs/testing jest @types/jest ts-jest
```

## Unit Testing Services

Unit tests isolate a single component and mock its dependencies.

### Basic Service Test

```typescript
// users.service.spec.ts
import { Test, TestingModule } from '@nestjs/testing';
import { UsersService } from './users.service';
import { UsersRepository } from './users.repository';

describe('UsersService', () => {
  let service: UsersService;
  let repository: jest.Mocked<UsersRepository>;

  beforeEach(async () => {
    const mockRepository = {
      findById: jest.fn(),
      findByEmail: jest.fn(),
      create: jest.fn(),
      update: jest.fn(),
      delete: jest.fn(),
    };

    const module: TestingModule = await Test.createTestingModule({
      providers: [
        UsersService,
        {
          provide: UsersRepository,
          useValue: mockRepository,
        },
      ],
    }).compile();

    service = module.get<UsersService>(UsersService);
    repository = module.get(UsersRepository);
  });

  describe('findById', () => {
    it('should return a user when found', async () => {
      const mockUser = { id: '1', email: 'test@example.com', name: 'Test' };
      repository.findById.mockResolvedValue(mockUser);

      const result = await service.findById('1');

      expect(result).toEqual(mockUser);
      expect(repository.findById).toHaveBeenCalledWith('1');
    });

    it('should throw NotFoundException when user not found', async () => {
      repository.findById.mockResolvedValue(null);

      await expect(service.findById('999')).rejects.toThrow(NotFoundException);
    });
  });

  describe('create', () => {
    it('should create and return a new user', async () => {
      const createDto = { email: 'new@example.com', name: 'New User' };
      const createdUser = { id: '2', ...createDto };

      repository.findByEmail.mockResolvedValue(null);
      repository.create.mockResolvedValue(createdUser);

      const result = await service.create(createDto);

      expect(result).toEqual(createdUser);
      expect(repository.create).toHaveBeenCalledWith(createDto);
    });

    it('should throw ConflictException when email exists', async () => {
      const createDto = { email: 'existing@example.com', name: 'User' };
      repository.findByEmail.mockResolvedValue({ id: '1', ...createDto });

      await expect(service.create(createDto)).rejects.toThrow(ConflictException);
    });
  });
});
```

### Testing with Custom Providers

When services have complex dependencies, use factory providers in tests:

```typescript
// orders.service.spec.ts
import { Test, TestingModule } from '@nestjs/testing';
import { OrdersService } from './orders.service';
import { PaymentService } from '../payment/payment.service';
import { InventoryService } from '../inventory/inventory.service';
import { NotificationService } from '../notification/notification.service';

describe('OrdersService', () => {
  let service: OrdersService;
  let paymentService: jest.Mocked<PaymentService>;
  let inventoryService: jest.Mocked<InventoryService>;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      providers: [
        OrdersService,
        {
          provide: PaymentService,
          useFactory: () => ({
            processPayment: jest.fn(),
            refund: jest.fn(),
          }),
        },
        {
          provide: InventoryService,
          useFactory: () => ({
            checkAvailability: jest.fn(),
            reserve: jest.fn(),
            release: jest.fn(),
          }),
        },
        {
          provide: NotificationService,
          useFactory: () => ({
            sendOrderConfirmation: jest.fn(),
            sendShippingUpdate: jest.fn(),
          }),
        },
      ],
    }).compile();

    service = module.get<OrdersService>(OrdersService);
    paymentService = module.get(PaymentService);
    inventoryService = module.get(InventoryService);
  });

  describe('placeOrder', () => {
    it('should process order successfully', async () => {
      const orderDto = {
        userId: '1',
        items: [{ productId: 'p1', quantity: 2 }],
        paymentMethod: 'card',
      };

      inventoryService.checkAvailability.mockResolvedValue(true);
      inventoryService.reserve.mockResolvedValue({ reservationId: 'r1' });
      paymentService.processPayment.mockResolvedValue({
        transactionId: 't1',
        status: 'success'
      });

      const result = await service.placeOrder(orderDto);

      expect(result.status).toBe('confirmed');
      expect(inventoryService.reserve).toHaveBeenCalled();
      expect(paymentService.processPayment).toHaveBeenCalled();
    });

    it('should release inventory on payment failure', async () => {
      const orderDto = {
        userId: '1',
        items: [{ productId: 'p1', quantity: 2 }],
        paymentMethod: 'card',
      };

      inventoryService.checkAvailability.mockResolvedValue(true);
      inventoryService.reserve.mockResolvedValue({ reservationId: 'r1' });
      paymentService.processPayment.mockRejectedValue(new Error('Payment failed'));

      await expect(service.placeOrder(orderDto)).rejects.toThrow('Payment failed');
      expect(inventoryService.release).toHaveBeenCalledWith('r1');
    });
  });
});
```

## Testing Controllers

Controller tests verify HTTP handling, validation, and response formatting.

```typescript
// users.controller.spec.ts
import { Test, TestingModule } from '@nestjs/testing';
import { UsersController } from './users.controller';
import { UsersService } from './users.service';
import { CreateUserDto } from './dto/create-user.dto';

describe('UsersController', () => {
  let controller: UsersController;
  let service: jest.Mocked<UsersService>;

  beforeEach(async () => {
    const mockService = {
      findAll: jest.fn(),
      findById: jest.fn(),
      create: jest.fn(),
      update: jest.fn(),
      delete: jest.fn(),
    };

    const module: TestingModule = await Test.createTestingModule({
      controllers: [UsersController],
      providers: [
        {
          provide: UsersService,
          useValue: mockService,
        },
      ],
    }).compile();

    controller = module.get<UsersController>(UsersController);
    service = module.get(UsersService);
  });

  describe('GET /users', () => {
    it('should return paginated users', async () => {
      const mockUsers = [
        { id: '1', email: 'user1@example.com' },
        { id: '2', email: 'user2@example.com' },
      ];
      service.findAll.mockResolvedValue({
        data: mockUsers,
        total: 2,
        page: 1,
        limit: 10,
      });

      const result = await controller.findAll({ page: 1, limit: 10 });

      expect(result.data).toHaveLength(2);
      expect(result.total).toBe(2);
    });
  });

  describe('POST /users', () => {
    it('should create a new user', async () => {
      const createDto: CreateUserDto = {
        email: 'new@example.com',
        name: 'New User',
        password: 'securepassword',
      };
      const createdUser = { id: '3', email: createDto.email, name: createDto.name };
      service.create.mockResolvedValue(createdUser);

      const result = await controller.create(createDto);

      expect(result).toEqual(createdUser);
      expect(service.create).toHaveBeenCalledWith(createDto);
    });
  });
});
```

## Integration Testing

Integration tests verify that multiple components work together correctly.

```typescript
// users.integration.spec.ts
import { Test, TestingModule } from '@nestjs/testing';
import { INestApplication, ValidationPipe } from '@nestjs/common';
import * as request from 'supertest';
import { AppModule } from '../app.module';
import { PrismaService } from '../prisma/prisma.service';

describe('Users Integration', () => {
  let app: INestApplication;
  let prisma: PrismaService;

  beforeAll(async () => {
    const moduleFixture: TestingModule = await Test.createTestingModule({
      imports: [AppModule],
    }).compile();

    app = moduleFixture.createNestApplication();
    app.useGlobalPipes(new ValidationPipe({ whitelist: true }));

    prisma = app.get(PrismaService);
    await app.init();
  });

  beforeEach(async () => {
    // Clean up database before each test
    await prisma.user.deleteMany();
  });

  afterAll(async () => {
    await prisma.$disconnect();
    await app.close();
  });

  describe('POST /users', () => {
    it('should create a user and return 201', async () => {
      const createDto = {
        email: 'integration@test.com',
        name: 'Integration Test',
        password: 'password123',
      };

      const response = await request(app.getHttpServer())
        .post('/users')
        .send(createDto)
        .expect(201);

      expect(response.body).toMatchObject({
        email: createDto.email,
        name: createDto.name,
      });
      expect(response.body).not.toHaveProperty('password');
      expect(response.body).toHaveProperty('id');
    });

    it('should return 400 for invalid email', async () => {
      const response = await request(app.getHttpServer())
        .post('/users')
        .send({
          email: 'invalid-email',
          name: 'Test',
          password: 'password123',
        })
        .expect(400);

      expect(response.body.message).toContain('email');
    });

    it('should return 409 for duplicate email', async () => {
      const createDto = {
        email: 'duplicate@test.com',
        name: 'First User',
        password: 'password123',
      };

      await request(app.getHttpServer())
        .post('/users')
        .send(createDto)
        .expect(201);

      await request(app.getHttpServer())
        .post('/users')
        .send({ ...createDto, name: 'Second User' })
        .expect(409);
    });
  });

  describe('GET /users/:id', () => {
    it('should return user by id', async () => {
      // Create a user first
      const createResponse = await request(app.getHttpServer())
        .post('/users')
        .send({
          email: 'findme@test.com',
          name: 'Find Me',
          password: 'password123',
        });

      const userId = createResponse.body.id;

      const response = await request(app.getHttpServer())
        .get(`/users/${userId}`)
        .expect(200);

      expect(response.body.email).toBe('findme@test.com');
    });

    it('should return 404 for non-existent user', async () => {
      await request(app.getHttpServer())
        .get('/users/non-existent-id')
        .expect(404);
    });
  });
});
```

## Testing Guards and Interceptors

### Testing a Guard

```typescript
// auth.guard.spec.ts
import { ExecutionContext, UnauthorizedException } from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import { AuthGuard } from './auth.guard';

describe('AuthGuard', () => {
  let guard: AuthGuard;
  let jwtService: jest.Mocked<JwtService>;

  beforeEach(() => {
    jwtService = {
      verifyAsync: jest.fn(),
    } as any;

    guard = new AuthGuard(jwtService);
  });

  const createMockContext = (authHeader?: string): ExecutionContext => {
    return {
      switchToHttp: () => ({
        getRequest: () => ({
          headers: {
            authorization: authHeader,
          },
        }),
      }),
    } as ExecutionContext;
  };

  it('should allow access with valid token', async () => {
    const mockPayload = { sub: '1', email: 'test@example.com' };
    jwtService.verifyAsync.mockResolvedValue(mockPayload);

    const context = createMockContext('Bearer valid-token');
    const result = await guard.canActivate(context);

    expect(result).toBe(true);
    expect(jwtService.verifyAsync).toHaveBeenCalledWith('valid-token');
  });

  it('should throw UnauthorizedException without token', async () => {
    const context = createMockContext();

    await expect(guard.canActivate(context)).rejects.toThrow(UnauthorizedException);
  });

  it('should throw UnauthorizedException with invalid token', async () => {
    jwtService.verifyAsync.mockRejectedValue(new Error('Invalid token'));

    const context = createMockContext('Bearer invalid-token');

    await expect(guard.canActivate(context)).rejects.toThrow(UnauthorizedException);
  });
});
```

### Testing an Interceptor

```typescript
// logging.interceptor.spec.ts
import { CallHandler, ExecutionContext } from '@nestjs/common';
import { of, throwError } from 'rxjs';
import { LoggingInterceptor } from './logging.interceptor';
import { Logger } from '../logger/logger.service';

describe('LoggingInterceptor', () => {
  let interceptor: LoggingInterceptor;
  let logger: jest.Mocked<Logger>;

  beforeEach(() => {
    logger = {
      log: jest.fn(),
      error: jest.fn(),
    } as any;

    interceptor = new LoggingInterceptor(logger);
  });

  const createMockContext = (): ExecutionContext => ({
    switchToHttp: () => ({
      getRequest: () => ({
        method: 'GET',
        url: '/users',
        headers: { 'x-request-id': 'test-123' },
      }),
    }),
    getClass: () => ({ name: 'UsersController' }),
    getHandler: () => ({ name: 'findAll' }),
  } as ExecutionContext);

  it('should log successful requests', (done) => {
    const context = createMockContext();
    const callHandler: CallHandler = {
      handle: () => of({ data: 'test' }),
    };

    interceptor.intercept(context, callHandler).subscribe({
      complete: () => {
        expect(logger.log).toHaveBeenCalledWith(
          expect.stringContaining('GET /users'),
          expect.any(Object)
        );
        done();
      },
    });
  });

  it('should log errors', (done) => {
    const context = createMockContext();
    const error = new Error('Test error');
    const callHandler: CallHandler = {
      handle: () => throwError(() => error),
    };

    interceptor.intercept(context, callHandler).subscribe({
      error: () => {
        expect(logger.error).toHaveBeenCalledWith(
          expect.stringContaining('GET /users'),
          expect.any(Object)
        );
        done();
      },
    });
  });
});
```

## E2E Testing Best Practices

### Test Database Setup

Create a separate test database configuration:

```typescript
// test/setup.ts
import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient({
  datasources: {
    db: {
      url: process.env.TEST_DATABASE_URL,
    },
  },
});

export async function setupTestDatabase() {
  await prisma.$executeRaw`TRUNCATE TABLE users CASCADE`;
  await prisma.$executeRaw`TRUNCATE TABLE orders CASCADE`;
}

export async function teardownTestDatabase() {
  await prisma.$disconnect();
}

export { prisma };
```

### Test Factories

Create factories for generating test data:

```typescript
// test/factories/user.factory.ts
import { faker } from '@faker-js/faker';
import { PrismaClient, User } from '@prisma/client';

export class UserFactory {
  constructor(private prisma: PrismaClient) {}

  async create(overrides: Partial<User> = {}): Promise<User> {
    return this.prisma.user.create({
      data: {
        email: faker.internet.email(),
        name: faker.person.fullName(),
        passwordHash: 'hashed-password',
        ...overrides,
      },
    });
  }

  async createMany(count: number, overrides: Partial<User> = {}): Promise<User[]> {
    return Promise.all(
      Array.from({ length: count }, () => this.create(overrides))
    );
  }
}
```

## Running Tests

```bash
# Run all unit tests
npm run test

# Run tests in watch mode
npm run test:watch

# Run tests with coverage
npm run test:cov

# Run e2e tests
npm run test:e2e

# Run specific test file
npm run test -- users.service.spec.ts
```

## Summary

- **Unit tests** isolate components with mocked dependencies
- **Integration tests** verify multiple components work together
- **E2E tests** test the full application stack
- Use **factories** to generate consistent test data
- Always **clean up** test data between tests
- Test **error cases** as thoroughly as success cases
