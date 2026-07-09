---
title: Exception Filters
description: Handle and transform exceptions into consistent API responses
category: core
relatedRules:
  - implement-global-exception-filter
  - use-proper-http-exceptions
---

# Exception Filters

Exception filters catch unhandled exceptions and transform them into appropriate HTTP responses. They provide a centralized place for error handling.

## Built-in HTTP Exceptions

NestJS provides standard HTTP exceptions:

```typescript
import {
  BadRequestException,      // 400
  UnauthorizedException,    // 401
  ForbiddenException,       // 403
  NotFoundException,        // 404
  ConflictException,        // 409
  UnprocessableEntityException, // 422
  InternalServerErrorException, // 500
} from '@nestjs/common';

// Usage
throw new NotFoundException('User not found');
throw new BadRequestException('Invalid email format');
throw new UnauthorizedException('Invalid credentials');
```

## Custom Exception Filter

```typescript
// filters/http-exception.filter.ts
import {
  ExceptionFilter,
  Catch,
  ArgumentsHost,
  HttpException,
  HttpStatus,
} from '@nestjs/common';
import { Request, Response } from 'express';

@Catch(HttpException)
export class HttpExceptionFilter implements ExceptionFilter {
  catch(exception: HttpException, host: ArgumentsHost) {
    const ctx = host.switchToHttp();
    const response = ctx.getResponse<Response>();
    const request = ctx.getRequest<Request>();
    const status = exception.getStatus();
    const exceptionResponse = exception.getResponse();

    const errorResponse = {
      statusCode: status,
      timestamp: new Date().toISOString(),
      path: request.url,
      method: request.method,
      message:
        typeof exceptionResponse === 'string'
          ? exceptionResponse
          : (exceptionResponse as any).message || 'An error occurred',
    };

    response.status(status).json(errorResponse);
  }
}
```

## Global Exception Filter

Catch all exceptions including non-HTTP ones:

```typescript
// filters/all-exceptions.filter.ts
@Catch()
export class AllExceptionsFilter implements ExceptionFilter {
  constructor(private logger: LoggerService) {}

  catch(exception: unknown, host: ArgumentsHost) {
    const ctx = host.switchToHttp();
    const response = ctx.getResponse<Response>();
    const request = ctx.getRequest<Request>();

    let status = HttpStatus.INTERNAL_SERVER_ERROR;
    let message = 'Internal server error';

    if (exception instanceof HttpException) {
      status = exception.getStatus();
      const res = exception.getResponse();
      message = typeof res === 'string' ? res : (res as any).message;
    } else if (exception instanceof Error) {
      message = exception.message;
      this.logger.error(
        `Unhandled exception: ${exception.message}`,
        exception.stack,
      );
    }

    response.status(status).json({
      statusCode: status,
      timestamp: new Date().toISOString(),
      path: request.url,
      message: status === 500 ? 'Internal server error' : message,
    });
  }
}
```

## Custom Business Exceptions

```typescript
// exceptions/business.exception.ts
export class BusinessException extends HttpException {
  constructor(
    public readonly code: string,
    message: string,
    status: HttpStatus = HttpStatus.BAD_REQUEST,
  ) {
    super({ code, message }, status);
  }
}

// exceptions/domain-exceptions.ts
export class InsufficientFundsException extends BusinessException {
  constructor() {
    super('INSUFFICIENT_FUNDS', 'Account has insufficient funds');
  }
}

export class OrderAlreadyShippedException extends BusinessException {
  constructor(orderId: string) {
    super(
      'ORDER_ALREADY_SHIPPED',
      `Order ${orderId} has already been shipped`,
      HttpStatus.CONFLICT,
    );
  }
}
```

## Applying Filters

```typescript
// Controller level
@UseFilters(HttpExceptionFilter)
@Controller('users')
export class UsersController {}

// Method level
@UseFilters(HttpExceptionFilter)
@Get()
findAll() {}

// Global (main.ts)
app.useGlobalFilters(new AllExceptionsFilter(logger));

// Global with DI (module)
{
  provide: APP_FILTER,
  useClass: AllExceptionsFilter,
}
```

## Filter Execution Order

When multiple filters are applied, they execute from most specific to most general:

```
Exception → Method Filter → Controller Filter → Global Filter
```

The first filter to handle the exception stops propagation.
