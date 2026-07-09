---
title: Module Architecture in NestJS
description: Learn how to structure your NestJS application with proper module organization
order: 2
category: architecture
difficulty: intermediate
estimatedTime: "20 min"
prerequisites:
  - getting-started
---

# Module Architecture in NestJS

Modules are the fundamental building blocks of NestJS applications. A well-organized module structure is the difference between a maintainable codebase and a tangled mess.

## The Module System

Every NestJS application has at least one module—the root `AppModule`. As your application grows, you'll create feature modules to organize related functionality.

```typescript
// app.module.ts
@Module({
  imports: [
    UsersModule,
    ProductsModule,
    OrdersModule,
    SharedModule,
  ],
})
export class AppModule {}
```

## Module Types

### Feature Modules

Feature modules encapsulate a specific domain or feature:

```typescript
// users/users.module.ts
@Module({
  imports: [TypeOrmModule.forFeature([User])],
  controllers: [UsersController],
  providers: [UsersService, UsersRepository],
  exports: [UsersService], // Only export what other modules need
})
export class UsersModule {}
```

**Key principles:**
- One feature = one module
- Keep modules focused and cohesive
- Only export what's needed by other modules

### Shared Modules

Shared modules contain utilities, helpers, and common functionality:

```typescript
// shared/shared.module.ts
@Module({
  providers: [
    LoggerService,
    CacheService,
    DateUtilsService,
  ],
  exports: [
    LoggerService,
    CacheService,
    DateUtilsService,
  ],
})
export class SharedModule {}
```

**Best practice:** Use `@Global()` sparingly. It's tempting to make shared modules global, but it hides dependencies and makes testing harder.

### Core Module

The core module contains singleton services used throughout the app:

```typescript
// core/core.module.ts
@Global()
@Module({
  providers: [
    ConfigService,
    DatabaseService,
    {
      provide: APP_GUARD,
      useClass: AuthGuard,
    },
  ],
  exports: [ConfigService, DatabaseService],
})
export class CoreModule {}
```

## Module Organization Patterns

### Flat Structure (Small Apps)

For small applications with < 10 modules:

```
src/
├── app.module.ts
├── users/
│   ├── users.module.ts
│   ├── users.controller.ts
│   ├── users.service.ts
│   └── dto/
├── products/
│   ├── products.module.ts
│   ├── products.controller.ts
│   └── products.service.ts
└── shared/
    └── shared.module.ts
```

### Domain-Driven Structure (Large Apps)

For larger applications, organize by domain:

```
src/
├── app.module.ts
├── core/
│   ├── core.module.ts
│   ├── config/
│   ├── database/
│   └── guards/
├── shared/
│   ├── shared.module.ts
│   ├── utils/
│   └── interceptors/
├── domains/
│   ├── users/
│   │   ├── users.module.ts
│   │   ├── application/        # Use cases
│   │   │   ├── create-user.ts
│   │   │   └── get-user.ts
│   │   ├── domain/             # Entities, value objects
│   │   │   └── user.entity.ts
│   │   ├── infrastructure/     # Repositories, external services
│   │   │   └── user.repository.ts
│   │   └── presentation/       # Controllers, DTOs
│   │       ├── users.controller.ts
│   │       └── dto/
│   └── orders/
│       └── ...
└── infrastructure/
    ├── database/
    ├── messaging/
    └── external-apis/
```

## Avoiding Common Mistakes

### Mistake 1: God Modules

```typescript
// ❌ Don't create modules that do everything
@Module({
  imports: [...],
  controllers: [
    UsersController,
    ProductsController,
    OrdersController,
    PaymentsController,
    // 20 more controllers...
  ],
  providers: [
    // 50 services...
  ],
})
export class EverythingModule {}
```

```typescript
// ✅ Split into focused feature modules
@Module({
  imports: [
    UsersModule,
    ProductsModule,
    OrdersModule,
    PaymentsModule,
  ],
})
export class AppModule {}
```

### Mistake 2: Tight Coupling

```typescript
// ❌ Direct service injection creates tight coupling
@Injectable()
export class OrdersService {
  constructor(
    private usersService: UsersService,
    private productsService: ProductsService,
    private paymentsService: PaymentsService,
    private shippingService: ShippingService,
    private notificationsService: NotificationsService,
  ) {}
}
```

```typescript
// ✅ Use events or interfaces for loose coupling
@Injectable()
export class OrdersService {
  constructor(
    private ordersRepository: OrdersRepository,
    private eventEmitter: EventEmitter2,
  ) {}

  async createOrder(dto: CreateOrderDto) {
    const order = await this.ordersRepository.create(dto);

    // Other services react to events, not direct calls
    this.eventEmitter.emit('order.created', order);

    return order;
  }
}
```

### Mistake 3: Barrel File Abuse

```typescript
// ❌ Don't re-export everything from a single index.ts
// shared/index.ts
export * from './logger.service';
export * from './cache.service';
export * from './utils';
export * from './constants';
// This creates implicit dependencies and circular import risks
```

```typescript
// ✅ Import from specific files
import { LoggerService } from './shared/logger.service';
import { CacheService } from './shared/cache.service';
```

## Dynamic Modules

For configurable modules, use the dynamic module pattern:

```typescript
// database/database.module.ts
@Module({})
export class DatabaseModule {
  static forRoot(options: DatabaseOptions): DynamicModule {
    return {
      module: DatabaseModule,
      global: true,
      providers: [
        {
          provide: 'DATABASE_OPTIONS',
          useValue: options,
        },
        DatabaseService,
      ],
      exports: [DatabaseService],
    };
  }

  static forFeature(entities: Type[]): DynamicModule {
    return {
      module: DatabaseModule,
      providers: entities.map(entity => ({
        provide: `${entity.name}Repository`,
        useFactory: (db: DatabaseService) => db.getRepository(entity),
        inject: [DatabaseService],
      })),
      exports: entities.map(entity => `${entity.name}Repository`),
    };
  }
}
```

Usage:

```typescript
// app.module.ts
@Module({
  imports: [
    DatabaseModule.forRoot({
      host: 'localhost',
      port: 5432,
    }),
  ],
})
export class AppModule {}

// users/users.module.ts
@Module({
  imports: [DatabaseModule.forFeature([User])],
})
export class UsersModule {}
```

## Module Testing

Test modules in isolation by mocking dependencies:

```typescript
// users/users.module.spec.ts
describe('UsersModule', () => {
  let module: TestingModule;

  beforeEach(async () => {
    module = await Test.createTestingModule({
      imports: [UsersModule],
    })
      .overrideProvider(UsersRepository)
      .useValue(mockUsersRepository)
      .compile();
  });

  it('should compile the module', () => {
    expect(module).toBeDefined();
  });

  it('should provide UsersService', () => {
    const service = module.get<UsersService>(UsersService);
    expect(service).toBeDefined();
  });
});
```

## Summary

| Pattern | When to Use |
|---------|-------------|
| Feature modules | Always—one module per feature |
| Shared modules | Cross-cutting utilities and helpers |
| Core module | App-wide singletons (config, database) |
| Dynamic modules | Configurable, reusable modules |
| Domain-driven structure | Large applications with complex domains |

## Additional Reading

- [Dependency Injection Deep Dive](/guides/dependency-injection) - Understand DI scopes and patterns
- [Avoiding Circular Dependencies](/rules/arch-avoid-circular-deps) - The #1 architecture killer
