---
title: Middleware
description: Process requests before they reach route handlers with Express-compatible middleware
category: core
relatedRules:
  - use-middleware-appropriately
  - implement-request-logging
---

# Middleware

Middleware functions run before route handlers. They have access to the request and response objects and can modify them or end the request-response cycle.

## Basic Middleware

```typescript
import { Injectable, NestMiddleware } from '@nestjs/common';
import { Request, Response, NextFunction } from 'express';

@Injectable()
export class LoggerMiddleware implements NestMiddleware {
  use(req: Request, res: Response, next: NextFunction) {
    const { method, originalUrl } = req;
    const start = Date.now();

    res.on('finish', () => {
      const duration = Date.now() - start;
      console.log(`${method} ${originalUrl} ${res.statusCode} - ${duration}ms`);
    });

    next();
  }
}
```

## Applying Middleware

```typescript
// app.module.ts
import { Module, NestModule, MiddlewareConsumer } from '@nestjs/common';

@Module({})
export class AppModule implements NestModule {
  configure(consumer: MiddlewareConsumer) {
    consumer
      .apply(LoggerMiddleware)
      .forRoutes('*'); // All routes

    consumer
      .apply(AuthMiddleware)
      .exclude({ path: 'auth/login', method: RequestMethod.POST })
      .forRoutes('users', 'orders');

    consumer
      .apply(RateLimitMiddleware)
      .forRoutes({ path: 'api/*', method: RequestMethod.ALL });
  }
}
```

## Common Middleware Patterns

### Request ID Middleware

```typescript
@Injectable()
export class RequestIdMiddleware implements NestMiddleware {
  use(req: Request, res: Response, next: NextFunction) {
    const requestId = req.headers['x-request-id'] || uuidv4();
    req['requestId'] = requestId;
    res.setHeader('x-request-id', requestId);
    next();
  }
}
```

### CORS Middleware

```typescript
// Using built-in CORS (recommended)
// main.ts
app.enableCors({
  origin: ['https://example.com'],
  methods: ['GET', 'POST', 'PUT', 'DELETE'],
  credentials: true,
});
```

### Compression

```typescript
// main.ts
import compression from 'compression';

app.use(compression());
```

## Middleware vs Interceptors vs Guards

| Feature | Middleware | Guards | Interceptors |
|---------|------------|--------|--------------|
| Access to ExecutionContext | No | Yes | Yes |
| Can access handler metadata | No | Yes | Yes |
| Can transform response | No | No | Yes |
| DI support | Yes | Yes | Yes |
| Best for | Raw request processing | Authorization | Response transformation |

## Functional Middleware

For simple cases, use functional middleware:

```typescript
export function logger(req: Request, res: Response, next: NextFunction) {
  console.log(`Request...`);
  next();
}

// Apply in module
consumer.apply(logger).forRoutes('*');
```
