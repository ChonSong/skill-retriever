---
title: Modules
description: How modules organize your NestJS application
order: 2
category: core
relatedRules:
  - arch-feature-modules
  - arch-avoid-circular-deps
---

# Modules

Modules are classes annotated with the `@Module()` decorator. They organize related functionality into cohesive units.

## Module Structure

```typescript
@Module({
  imports: [],      // Other modules this module depends on
  controllers: [],  // Controllers defined in this module
  providers: [],    // Services, repositories, etc.
  exports: [],      // Providers available to other modules
})
export class UsersModule {}
```

## The Root Module

Every NestJS app has a root module—typically `AppModule`:

```typescript
@Module({
  imports: [
    ConfigModule.forRoot(),
    DatabaseModule,
    UsersModule,
    ProductsModule,
  ],
})
export class AppModule {}
```

## Module Encapsulation

By default, providers are **private** to their module:

```typescript
// users.module.ts
@Module({
  providers: [UsersService, UsersRepository],
  exports: [UsersService], // Only UsersService is accessible outside
})
export class UsersModule {}

// orders.module.ts
@Module({
  imports: [UsersModule],
  providers: [OrdersService],
})
export class OrdersModule {}

// orders.service.ts
@Injectable()
export class OrdersService {
  constructor(
    private usersService: UsersService, // ✅ Works - exported
    // private usersRepository: UsersRepository, // ❌ Error - not exported
  ) {}
}
```

## Dynamic Modules

Modules can be configured dynamically:

```typescript
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
}

// Usage
@Module({
  imports: [
    DatabaseModule.forRoot({
      host: 'localhost',
      port: 5432,
    }),
  ],
})
export class AppModule {}
```

## Global Modules

Use `@Global()` for truly application-wide services:

```typescript
@Global()
@Module({
  providers: [ConfigService, LoggerService],
  exports: [ConfigService, LoggerService],
})
export class CoreModule {}
```

**Warning:** Overusing global modules makes dependencies implicit and harder to test.

## Module Best Practices

1. **One feature per module** - Keep modules focused
2. **Avoid circular imports** - Refactor if modules depend on each other
3. **Minimize exports** - Only export what other modules need
4. **Use dynamic modules** - For configurable, reusable modules

## Related

- [Module Architecture Guide](/guides/module-architecture)
- [Avoid Circular Dependencies](/rules/arch-avoid-circular-deps)
