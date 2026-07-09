---
title: Error Handling Patterns
description: Build robust and consistent error handling in your NestJS applications
order: 4
category: fundamentals
difficulty: intermediate
estimatedTime: "20 min"
prerequisites:
  - getting-started
---

# Error Handling Patterns

Proper error handling separates professional applications from fragile ones. NestJS provides powerful tools for handling errors consistently across your application.

## The Exception Layer

NestJS has a built-in exception layer that catches unhandled exceptions and converts them to appropriate HTTP responses.

### Built-in HTTP Exceptions

NestJS provides exceptions for common HTTP error codes:

```typescript
import {
  BadRequestException,
  UnauthorizedException,
  ForbiddenException,
  NotFoundException,
  ConflictException,
  InternalServerErrorException,
} from '@nestjs/common';

@Injectable()
export class UsersService {
  async findById(id: string) {
    const user = await this.repo.findOne(id);

    if (!user) {
      throw new NotFoundException(`User with ID ${id} not found`);
    }

    return user;
  }

  async create(dto: CreateUserDto) {
    const existing = await this.repo.findByEmail(dto.email);

    if (existing) {
      throw new ConflictException('Email already registered');
    }

    return this.repo.create(dto);
  }
}
```

### Exception Response Format

Built-in exceptions produce consistent responses:

```json
{
  "statusCode": 404,
  "message": "User with ID 123 not found",
  "error": "Not Found"
}
```

## Custom Exceptions

Create domain-specific exceptions for better error handling:

```typescript
// exceptions/user-not-found.exception.ts
export class UserNotFoundException extends NotFoundException {
  constructor(userId: string) {
    super({
      code: 'USER_NOT_FOUND',
      message: `User with ID ${userId} not found`,
      userId,
    });
  }
}

// exceptions/email-already-exists.exception.ts
export class EmailAlreadyExistsException extends ConflictException {
  constructor(email: string) {
    super({
      code: 'EMAIL_ALREADY_EXISTS',
      message: 'This email is already registered',
      email,
    });
  }
}

// Usage
throw new UserNotFoundException(userId);
throw new EmailAlreadyExistsException(dto.email);
```

### Business Logic Exceptions

For domain errors that aren't HTTP-specific:

```typescript
// exceptions/domain.exception.ts
export class DomainException extends Error {
  constructor(
    public readonly code: string,
    message: string,
    public readonly details?: Record<string, unknown>,
  ) {
    super(message);
    this.name = 'DomainException';
  }
}

export class InsufficientFundsException extends DomainException {
  constructor(available: number, required: number) {
    super(
      'INSUFFICIENT_FUNDS',
      `Insufficient funds: ${available} available, ${required} required`,
      { available, required },
    );
  }
}

export class OrderAlreadyShippedException extends DomainException {
  constructor(orderId: string) {
    super(
      'ORDER_ALREADY_SHIPPED',
      `Order ${orderId} has already been shipped`,
      { orderId },
    );
  }
}
```

## Exception Filters

Exception filters intercept exceptions and transform responses.

### Global Exception Filter

Create a consistent error response format across your API:

```typescript
// filters/all-exceptions.filter.ts
import {
  ExceptionFilter,
  Catch,
  ArgumentsHost,
  HttpException,
  HttpStatus,
  Logger,
} from '@nestjs/common';
import { Request, Response } from 'express';

interface ErrorResponse {
  statusCode: number;
  code: string;
  message: string;
  timestamp: string;
  path: string;
  details?: Record<string, unknown>;
}

@Catch()
export class AllExceptionsFilter implements ExceptionFilter {
  private readonly logger = new Logger(AllExceptionsFilter.name);

  catch(exception: unknown, host: ArgumentsHost) {
    const ctx = host.switchToHttp();
    const response = ctx.getResponse<Response>();
    const request = ctx.getRequest<Request>();

    const errorResponse = this.buildErrorResponse(exception, request);

    // Log the error
    this.logError(exception, errorResponse);

    response.status(errorResponse.statusCode).json(errorResponse);
  }

  private buildErrorResponse(exception: unknown, request: Request): ErrorResponse {
    if (exception instanceof HttpException) {
      const status = exception.getStatus();
      const exceptionResponse = exception.getResponse();

      return {
        statusCode: status,
        code: this.extractCode(exceptionResponse),
        message: this.extractMessage(exceptionResponse),
        timestamp: new Date().toISOString(),
        path: request.url,
        details: this.extractDetails(exceptionResponse),
      };
    }

    if (exception instanceof DomainException) {
      return {
        statusCode: HttpStatus.UNPROCESSABLE_ENTITY,
        code: exception.code,
        message: exception.message,
        timestamp: new Date().toISOString(),
        path: request.url,
        details: exception.details,
      };
    }

    // Unknown error - don't leak internal details
    return {
      statusCode: HttpStatus.INTERNAL_SERVER_ERROR,
      code: 'INTERNAL_ERROR',
      message: 'An unexpected error occurred',
      timestamp: new Date().toISOString(),
      path: request.url,
    };
  }

  private extractCode(response: string | object): string {
    if (typeof response === 'object' && 'code' in response) {
      return response.code as string;
    }
    return 'ERROR';
  }

  private extractMessage(response: string | object): string {
    if (typeof response === 'string') {
      return response;
    }
    if ('message' in response) {
      return Array.isArray(response.message)
        ? response.message[0]
        : response.message;
    }
    return 'An error occurred';
  }

  private extractDetails(response: string | object): Record<string, unknown> | undefined {
    if (typeof response === 'object') {
      const { statusCode, message, error, code, ...details } = response as Record<string, unknown>;
      return Object.keys(details).length > 0 ? details : undefined;
    }
    return undefined;
  }

  private logError(exception: unknown, errorResponse: ErrorResponse) {
    if (errorResponse.statusCode >= 500) {
      this.logger.error(
        `${errorResponse.code}: ${errorResponse.message}`,
        exception instanceof Error ? exception.stack : undefined,
      );
    } else {
      this.logger.warn(`${errorResponse.code}: ${errorResponse.message}`);
    }
  }
}
```

Register the filter globally:

```typescript
// main.ts
async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  app.useGlobalFilters(new AllExceptionsFilter());
  await app.listen(3000);
}
```

Or via the module system (preferred for DI access):

```typescript
// app.module.ts
@Module({
  providers: [
    {
      provide: APP_FILTER,
      useClass: AllExceptionsFilter,
    },
  ],
})
export class AppModule {}
```

### Specific Exception Filters

Handle specific exception types differently:

```typescript
// filters/validation.filter.ts
@Catch(BadRequestException)
export class ValidationExceptionFilter implements ExceptionFilter {
  catch(exception: BadRequestException, host: ArgumentsHost) {
    const ctx = host.switchToHttp();
    const response = ctx.getResponse<Response>();
    const exceptionResponse = exception.getResponse() as any;

    response.status(400).json({
      statusCode: 400,
      code: 'VALIDATION_ERROR',
      message: 'Validation failed',
      errors: this.formatValidationErrors(exceptionResponse.message),
      timestamp: new Date().toISOString(),
    });
  }

  private formatValidationErrors(messages: string | string[]) {
    if (typeof messages === 'string') {
      return [{ field: 'unknown', message: messages }];
    }

    return messages.map(msg => {
      // Parse class-validator error format
      const match = msg.match(/^(\w+)\s+(.+)$/);
      return match
        ? { field: match[1], message: match[2] }
        : { field: 'unknown', message: msg };
    });
  }
}
```

## Async Error Handling

### Promises in Services

Always handle async errors properly:

```typescript
@Injectable()
export class UsersService {
  // ❌ Unhandled promise rejection if DB fails
  async createBad(dto: CreateUserDto) {
    return this.repo.save(dto);
  }

  // ✅ Proper error handling
  async create(dto: CreateUserDto) {
    try {
      return await this.repo.save(dto);
    } catch (error) {
      if (error.code === '23505') {
        // Postgres unique violation
        throw new ConflictException('User already exists');
      }
      throw error; // Re-throw unknown errors
    }
  }
}
```

### Concurrent Operations

Handle errors in Promise.all:

```typescript
// ❌ Fails fast, loses other results
async processAllBad(ids: string[]) {
  return Promise.all(ids.map(id => this.process(id)));
}

// ✅ Collect all results and errors
async processAll(ids: string[]) {
  const results = await Promise.allSettled(
    ids.map(id => this.process(id))
  );

  const successes = results
    .filter((r): r is PromiseFulfilledResult<any> => r.status === 'fulfilled')
    .map(r => r.value);

  const failures = results
    .filter((r): r is PromiseRejectedResult => r.status === 'rejected')
    .map((r, i) => ({ id: ids[i], error: r.reason.message }));

  return { successes, failures };
}
```

## Error Handling in Controllers

### Consistent Response Wrapper

Use a standard response format:

```typescript
// dto/api-response.dto.ts
export class ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
  };

  static success<T>(data: T): ApiResponse<T> {
    return { success: true, data };
  }

  static error(code: string, message: string): ApiResponse<never> {
    return { success: false, error: { code, message } };
  }
}

// users.controller.ts
@Controller('users')
export class UsersController {
  @Get(':id')
  async findOne(@Param('id') id: string) {
    const user = await this.usersService.findById(id);
    return ApiResponse.success(user);
  }
}
```

### Input Validation

Use class-validator for input validation:

```typescript
// dto/create-user.dto.ts
import { IsEmail, IsString, MinLength, IsOptional } from 'class-validator';

export class CreateUserDto {
  @IsEmail({}, { message: 'Please provide a valid email address' })
  email: string;

  @IsString()
  @MinLength(8, { message: 'Password must be at least 8 characters' })
  password: string;

  @IsOptional()
  @IsString()
  name?: string;
}

// main.ts
app.useGlobalPipes(
  new ValidationPipe({
    whitelist: true,           // Strip unknown properties
    forbidNonWhitelisted: true, // Throw on unknown properties
    transform: true,           // Auto-transform types
  }),
);
```

## Logging Errors

Integrate structured logging:

```typescript
// services/logger.service.ts
@Injectable()
export class AppLogger {
  private logger = new Logger();

  error(context: string, error: Error, metadata?: Record<string, unknown>) {
    this.logger.error(
      {
        message: error.message,
        stack: error.stack,
        ...metadata,
      },
      error.stack,
      context,
    );
  }

  warn(context: string, message: string, metadata?: Record<string, unknown>) {
    this.logger.warn({ message, ...metadata }, context);
  }
}

// Usage in exception filter
@Catch()
export class AllExceptionsFilter implements ExceptionFilter {
  constructor(private readonly logger: AppLogger) {}

  catch(exception: unknown, host: ArgumentsHost) {
    // ... build response

    if (exception instanceof Error) {
      this.logger.error('ExceptionFilter', exception, {
        path: request.url,
        method: request.method,
        statusCode: errorResponse.statusCode,
      });
    }

    // ... send response
  }
}
```

## Summary

| Pattern | Use Case |
|---------|----------|
| Built-in exceptions | Standard HTTP errors |
| Custom HTTP exceptions | Domain-specific errors with extra context |
| Domain exceptions | Business logic errors |
| Global exception filter | Consistent response format |
| Specific filters | Handle certain errors differently |
| ValidationPipe | Input validation |
| Structured logging | Error tracking and debugging |

## Additional Reading

- [Use Exception Filters](/rules/error-use-exception-filters) - Detailed rule on filters
- [Handle Async Errors](/rules/error-handle-async-errors) - Async patterns
- [Security Best Practices](/guides/security) - Secure error handling
