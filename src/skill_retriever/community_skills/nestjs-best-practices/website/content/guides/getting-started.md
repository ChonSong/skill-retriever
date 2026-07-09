---
title: Getting Started with NestJS Best Practices
description: Learn how to apply best practices to your NestJS applications from day one
order: 1
category: fundamentals
difficulty: beginner
estimatedTime: "15 min"
prerequisites: []
---

# Getting Started with NestJS Best Practices

Welcome to the NestJS Best Practices guide. This documentation is designed for both humans and AI agents—because **skills aren't only for AI**.

## Why Best Practices Matter

NestJS provides powerful abstractions, but with power comes responsibility. Following established patterns helps you:

- **Avoid common pitfalls** that lead to runtime errors
- **Build maintainable code** that scales with your team
- **Improve testability** through proper dependency injection
- **Enhance security** by following proven patterns

## How This Guide is Organized

The best practices are organized into **10 categories**, prioritized by impact:

| Category | Impact | Focus |
|----------|--------|-------|
| Architecture | CRITICAL | Module organization, avoiding circular deps |
| Dependency Injection | CRITICAL | Proper DI patterns, scopes, tokens |
| Error Handling | HIGH | Exception filters, consistent errors |
| Security | HIGH | Input validation, auth, guards |
| Performance | HIGH | Caching, async patterns, optimization |
| Testing | MEDIUM-HIGH | Unit tests, e2e tests, mocking |
| Database | MEDIUM-HIGH | Transactions, N+1 prevention |
| API Design | MEDIUM | DTOs, versioning, interceptors |
| Microservices | MEDIUM | Patterns, health checks, queues |
| DevOps | LOW-MEDIUM | Config, logging, graceful shutdown |

## Your First Best Practice

Let's start with the most impactful rule: **avoiding circular dependencies**.

### The Problem

Circular dependencies occur when Module A imports Module B, and Module B imports Module A:

```typescript
// ❌ This will cause runtime errors

// users.module.ts
@Module({
  imports: [OrdersModule], // Orders needs Users
  providers: [UsersService],
  exports: [UsersService],
})
export class UsersModule {}

// orders.module.ts
@Module({
  imports: [UsersModule], // Users needs Orders = circular!
  providers: [OrdersService],
})
export class OrdersModule {}
```

### The Solution

Extract shared functionality to a third module, or use events for decoupled communication:

```typescript
// ✅ Option 1: Extract shared logic

// shared.module.ts
@Module({
  providers: [SharedService],
  exports: [SharedService],
})
export class SharedModule {}

// users.module.ts
@Module({
  imports: [SharedModule],
  providers: [UsersService],
})
export class UsersModule {}

// orders.module.ts
@Module({
  imports: [SharedModule],
  providers: [OrdersService],
})
export class OrdersModule {}
```

```typescript
// ✅ Option 2: Use events for decoupled communication

// users.service.ts
@Injectable()
export class UsersService {
  constructor(private eventEmitter: EventEmitter2) {}

  async createUser(data: CreateUserDto) {
    const user = await this.userRepo.save(data);
    this.eventEmitter.emit('user.created', user);
    return user;
  }
}

// orders.service.ts
@Injectable()
export class OrdersService {
  @OnEvent('user.created')
  handleUserCreated(user: User) {
    // React to user creation without direct dependency
  }
}
```

## Additional Reading

Now that you understand the basics, explore these foundational guides:

- [Module Architecture](/guides/module-architecture) - How to structure your modules
- [Dependency Injection Deep Dive](/guides/dependency-injection) - Master NestJS DI
- [Error Handling Patterns](/guides/error-handling) - Build robust error handling

Or jump directly to the [Rules Reference](/rules) to browse all 40+ best practices.
