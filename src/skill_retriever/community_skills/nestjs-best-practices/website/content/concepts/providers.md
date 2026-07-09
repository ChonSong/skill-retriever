---
title: Providers
description: Understanding providers - the fundamental building block of NestJS
order: 1
category: core
relatedRules:
  - di-prefer-constructor-injection
  - di-scope-awareness
---

# Providers

Providers are the fundamental building block of NestJS. They can be services, repositories, factories, helpers, or any class that can be **injected** as a dependency.

## What Makes a Provider?

Any class decorated with `@Injectable()` can be a provider:

```typescript
import { Injectable } from '@nestjs/common';

@Injectable()
export class UsersService {
  private users: User[] = [];

  findAll(): User[] {
    return this.users;
  }

  create(user: User): User {
    this.users.push(user);
    return user;
  }
}
```

The `@Injectable()` decorator attaches metadata that allows NestJS to manage the class through its IoC (Inversion of Control) container.

## Registering Providers

Providers must be registered in a module to be available:

```typescript
@Module({
  providers: [UsersService],
  exports: [UsersService], // Make available to other modules
})
export class UsersModule {}
```

## Provider Syntax Variations

### Standard Provider

```typescript
providers: [UsersService]

// Equivalent to:
providers: [
  {
    provide: UsersService,
    useClass: UsersService,
  }
]
```

### Custom Token

```typescript
providers: [
  {
    provide: 'USERS_SERVICE',
    useClass: UsersService,
  }
]

// Inject with:
constructor(@Inject('USERS_SERVICE') private usersService: UsersService) {}
```

### Value Provider

```typescript
providers: [
  {
    provide: 'CONFIG',
    useValue: {
      apiUrl: 'https://api.example.com',
      timeout: 5000,
    },
  }
]
```

### Factory Provider

```typescript
providers: [
  {
    provide: 'DATABASE_CONNECTION',
    useFactory: async (config: ConfigService) => {
      return createConnection(config.get('database'));
    },
    inject: [ConfigService],
  }
]
```

## The Provider Lifecycle

1. **Registration** - Provider is registered in a module
2. **Resolution** - NestJS resolves dependencies when needed
3. **Instantiation** - Instance is created (once for singletons)
4. **Injection** - Instance is injected where requested
5. **Destruction** - Instance is destroyed when app shuts down

## Best Practices

1. **Keep providers focused** - Single responsibility
2. **Use interfaces** - Define contracts for better testing
3. **Prefer constructor injection** - Makes dependencies explicit
4. **Export only what's needed** - Minimize public API

## Related

- [Dependency Injection Guide](/guides/dependency-injection)
- [Prefer Constructor Injection](/rules/di-prefer-constructor-injection)
