---
title: Interceptors
description: Transform responses, add logging, handle caching, and implement cross-cutting concerns
category: core
relatedRules:
  - use-interceptors-for-response-transformation
  - implement-proper-logging
---

# Interceptors

Interceptors are powerful components that can transform the result returned from a function, transform exceptions thrown, extend basic function behavior, or completely override a function.

## How Interceptors Work

Interceptors wrap the route handler execution. They have access to the execution context before and after the handler runs:

```
Request → Interceptor (before) → Handler → Interceptor (after) → Response
```

## Basic Interceptor Structure

```typescript
import {
  Injectable,
  NestInterceptor,
  ExecutionContext,
  CallHandler,
} from '@nestjs/common';
import { Observable } from 'rxjs';
import { tap, map } from 'rxjs/operators';

@Injectable()
export class LoggingInterceptor implements NestInterceptor {
  intercept(context: ExecutionContext, next: CallHandler): Observable<any> {
    const request = context.switchToHttp().getRequest();
    const { method, url } = request;
    const now = Date.now();

    console.log(`[${method}] ${url} - Request started`);

    return next.handle().pipe(
      tap(() => {
        console.log(`[${method}] ${url} - ${Date.now() - now}ms`);
      }),
    );
  }
}
```

## Common Use Cases

### Response Transformation

Wrap all responses in a consistent format:

```typescript
@Injectable()
export class TransformInterceptor<T> implements NestInterceptor<T, Response<T>> {
  intercept(context: ExecutionContext, next: CallHandler): Observable<Response<T>> {
    return next.handle().pipe(
      map((data) => ({
        success: true,
        data,
        timestamp: new Date().toISOString(),
      })),
    );
  }
}
```

### Caching

```typescript
@Injectable()
export class CacheInterceptor implements NestInterceptor {
  constructor(private cacheService: CacheService) {}

  async intercept(context: ExecutionContext, next: CallHandler) {
    const request = context.switchToHttp().getRequest();
    const cacheKey = `${request.method}:${request.url}`;

    const cached = await this.cacheService.get(cacheKey);
    if (cached) {
      return of(cached);
    }

    return next.handle().pipe(
      tap((data) => this.cacheService.set(cacheKey, data, 300)),
    );
  }
}
```

### Timeout Handling

```typescript
@Injectable()
export class TimeoutInterceptor implements NestInterceptor {
  intercept(context: ExecutionContext, next: CallHandler): Observable<any> {
    return next.handle().pipe(
      timeout(5000),
      catchError((err) => {
        if (err instanceof TimeoutError) {
          throw new RequestTimeoutException('Request timed out');
        }
        throw err;
      }),
    );
  }
}
```

## Applying Interceptors

```typescript
// Controller level
@UseInterceptors(LoggingInterceptor)
@Controller('users')
export class UsersController {}

// Method level
@UseInterceptors(CacheInterceptor)
@Get()
findAll() {}

// Global level (in main.ts)
app.useGlobalInterceptors(new LoggingInterceptor());

// Global with DI (in module)
{
  provide: APP_INTERCEPTOR,
  useClass: LoggingInterceptor,
}
```

## Execution Order

When multiple interceptors are applied, they execute in order for requests and reverse order for responses:

```
Request → Interceptor1 → Interceptor2 → Handler → Interceptor2 → Interceptor1 → Response
```
