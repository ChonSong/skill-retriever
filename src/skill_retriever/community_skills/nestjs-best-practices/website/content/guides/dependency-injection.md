---
title: Dependency Injection Deep Dive
description: Master NestJS dependency injection patterns, scopes, and advanced techniques
order: 3
category: fundamentals
difficulty: intermediate
estimatedTime: "25 min"
prerequisites:
  - getting-started
  - module-architecture
---

# Dependency Injection Deep Dive

Dependency Injection (DI) is the backbone of NestJS. Understanding it deeply will make your code more testable, maintainable, and flexible.

## How NestJS DI Works

NestJS uses an IoC (Inversion of Control) container to manage dependencies. When you decorate a class with `@Injectable()`, NestJS:

1. Registers the class as a provider
2. Analyzes its constructor parameters
3. Resolves dependencies recursively
4. Instantiates and caches the instance

```typescript
@Injectable()
export class UsersService {
  // NestJS automatically injects UsersRepository
  constructor(private readonly usersRepository: UsersRepository) {}
}
```

## Provider Types

### Standard Providers

The most common pattern—a class decorated with `@Injectable()`:

```typescript
// users.service.ts
@Injectable()
export class UsersService {
  constructor(private readonly repo: UsersRepository) {}

  findAll() {
    return this.repo.find();
  }
}

// users.module.ts
@Module({
  providers: [UsersService, UsersRepository],
})
export class UsersModule {}
```

### Value Providers

Inject static values or configuration:

```typescript
@Module({
  providers: [
    {
      provide: 'API_KEY',
      useValue: process.env.API_KEY,
    },
    {
      provide: 'CONFIG',
      useValue: {
        timeout: 5000,
        retries: 3,
      },
    },
  ],
})
export class AppModule {}

// Usage
@Injectable()
export class ApiService {
  constructor(@Inject('API_KEY') private apiKey: string) {}
}
```

### Factory Providers

Create providers dynamically based on other dependencies:

```typescript
@Module({
  providers: [
    ConfigService,
    {
      provide: 'DATABASE_CONNECTION',
      useFactory: async (config: ConfigService) => {
        const options = config.get('database');
        return createConnection(options);
      },
      inject: [ConfigService],
    },
  ],
})
export class DatabaseModule {}
```

### Class Providers

Substitute one class for another (great for testing):

```typescript
@Module({
  providers: [
    {
      provide: PaymentService,
      useClass: process.env.NODE_ENV === 'test'
        ? MockPaymentService
        : StripePaymentService,
    },
  ],
})
export class PaymentsModule {}
```

### Existing Providers (Aliases)

Create aliases for existing providers:

```typescript
@Module({
  providers: [
    UsersService,
    {
      provide: 'AliasedUsersService',
      useExisting: UsersService,
    },
  ],
})
export class UsersModule {}
```

## Injection Scopes

### Default Scope (Singleton)

By default, providers are singletons—one instance shared across the entire application:

```typescript
@Injectable() // Singleton by default
export class UsersService {}
```

**Use when:** The service is stateless or maintains application-wide state.

### Request Scope

A new instance is created for each incoming request:

```typescript
@Injectable({ scope: Scope.REQUEST })
export class RequestContextService {
  private requestId: string;

  setRequestId(id: string) {
    this.requestId = id;
  }

  getRequestId() {
    return this.requestId;
  }
}
```

**Use when:** You need per-request state (current user, request ID, tenant).

**Warning:** Request-scoped providers bubble up. If `ServiceA` (singleton) depends on `ServiceB` (request-scoped), `ServiceA` becomes request-scoped too.

### Transient Scope

A new instance is created for each injection:

```typescript
@Injectable({ scope: Scope.TRANSIENT })
export class HelperService {
  private id = Math.random();

  getId() {
    return this.id;
  }
}
```

**Use when:** Each consumer needs its own isolated instance.

### Scope Hierarchy

```
Singleton (default)
    └── Shared across entire app
    └── Created once at startup

Request
    └── New instance per HTTP request
    └── Shared within a single request
    └── ⚠️ Performance impact

Transient
    └── New instance per injection
    └── Never shared
    └── ⚠️ Higher memory usage
```

## Injection Tokens

### String Tokens

Simple but prone to typos:

```typescript
// ❌ Fragile - string literals
providers: [{ provide: 'USER_REPO', useClass: UsersRepository }]

// Injection
constructor(@Inject('USER_REPO') private repo: UsersRepository) {}
```

### Symbol Tokens

Type-safe but verbose:

```typescript
export const USER_REPO = Symbol('USER_REPO');

providers: [{ provide: USER_REPO, useClass: UsersRepository }]

// Injection
constructor(@Inject(USER_REPO) private repo: UsersRepository) {}
```

### InjectionToken Class (Recommended)

Best practice—type-safe and self-documenting:

```typescript
// tokens.ts
import { InjectionToken } from '@nestjs/common';

export interface DatabaseConfig {
  host: string;
  port: number;
}

export const DATABASE_CONFIG = new InjectionToken<DatabaseConfig>('DATABASE_CONFIG');

// module
providers: [
  {
    provide: DATABASE_CONFIG,
    useValue: { host: 'localhost', port: 5432 },
  },
]

// service
constructor(@Inject(DATABASE_CONFIG) private config: DatabaseConfig) {}
```

## Interface-Based Injection

NestJS can't use interfaces as tokens (TypeScript interfaces don't exist at runtime), but you can achieve the same pattern:

```typescript
// interfaces/user-repository.interface.ts
export interface IUserRepository {
  findById(id: string): Promise<User | null>;
  save(user: User): Promise<User>;
}

export const USER_REPOSITORY = Symbol('USER_REPOSITORY');

// repositories/user.repository.ts
@Injectable()
export class UserRepository implements IUserRepository {
  async findById(id: string) { /* ... */ }
  async save(user: User) { /* ... */ }
}

// users.module.ts
@Module({
  providers: [
    {
      provide: USER_REPOSITORY,
      useClass: UserRepository,
    },
  ],
})
export class UsersModule {}

// users.service.ts
@Injectable()
export class UsersService {
  constructor(
    @Inject(USER_REPOSITORY) private readonly repo: IUserRepository,
  ) {}
}
```

This pattern enables:
- Easy mocking in tests
- Swappable implementations
- Clear contracts between layers

## Circular Dependency Resolution

When two services depend on each other:

```typescript
// ❌ Circular dependency error
@Injectable()
export class ServiceA {
  constructor(private serviceB: ServiceB) {}
}

@Injectable()
export class ServiceB {
  constructor(private serviceA: ServiceA) {}
}
```

**Solution 1: Forward Reference**

```typescript
@Injectable()
export class ServiceA {
  constructor(
    @Inject(forwardRef(() => ServiceB))
    private serviceB: ServiceB,
  ) {}
}

@Injectable()
export class ServiceB {
  constructor(
    @Inject(forwardRef(() => ServiceA))
    private serviceA: ServiceA,
  ) {}
}
```

**Solution 2: Refactor (Preferred)**

Extract shared logic or use events to break the cycle:

```typescript
// ✅ Better architecture
@Injectable()
export class ServiceA {
  constructor(private eventEmitter: EventEmitter2) {}

  doSomething() {
    this.eventEmitter.emit('something.done', data);
  }
}

@Injectable()
export class ServiceB {
  @OnEvent('something.done')
  handleSomethingDone(data: any) {
    // React without direct dependency
  }
}
```

## Optional Dependencies

When a dependency might not be available:

```typescript
@Injectable()
export class NotificationService {
  constructor(
    @Optional() @Inject('SLACK_CLIENT') private slack?: SlackClient,
    @Optional() @Inject('EMAIL_CLIENT') private email?: EmailClient,
  ) {}

  notify(message: string) {
    this.slack?.send(message);
    this.email?.send(message);
  }
}
```

## Self-Injection

Access the current provider from within itself (useful for proxying):

```typescript
@Injectable()
export class UsersService {
  constructor(
    @Inject(INQUIRER) private parentClass: object,
    private moduleRef: ModuleRef,
  ) {}

  // Get a fresh instance of this service
  async getNewInstance() {
    return this.moduleRef.resolve(UsersService);
  }
}
```

## Testing with DI

Override providers easily in tests:

```typescript
describe('UsersService', () => {
  let service: UsersService;
  let mockRepo: jest.Mocked<IUserRepository>;

  beforeEach(async () => {
    mockRepo = {
      findById: jest.fn(),
      save: jest.fn(),
    };

    const module = await Test.createTestingModule({
      providers: [
        UsersService,
        {
          provide: USER_REPOSITORY,
          useValue: mockRepo,
        },
      ],
    }).compile();

    service = module.get<UsersService>(UsersService);
  });

  it('should find user by id', async () => {
    const user = { id: '1', name: 'Test' };
    mockRepo.findById.mockResolvedValue(user);

    const result = await service.findById('1');

    expect(result).toEqual(user);
    expect(mockRepo.findById).toHaveBeenCalledWith('1');
  });
});
```

## Summary

| Pattern | When to Use |
|---------|-------------|
| `@Injectable()` | Standard services |
| `useValue` | Static config, constants |
| `useFactory` | Dynamic creation with deps |
| `useClass` | Conditional implementations |
| `Scope.REQUEST` | Per-request state |
| `Scope.TRANSIENT` | Isolated instances |
| Interface + Token | Clean architecture, testability |

## Additional Reading

- [Error Handling Patterns](/guides/error-handling) - Build robust error handling
- [DI Scope Awareness](/rules/di-scope-awareness) - Understand scope implications
