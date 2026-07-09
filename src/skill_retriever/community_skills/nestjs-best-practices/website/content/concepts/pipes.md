---
title: Pipes
description: Transform and validate incoming data before it reaches route handlers
category: core
relatedRules:
  - use-validation-pipes
  - implement-dto-validation
---

# Pipes

Pipes transform input data or validate it before it reaches route handlers. They operate on the arguments being processed.

## Built-in Pipes

NestJS provides several built-in pipes:

```typescript
import {
  ValidationPipe,
  ParseIntPipe,
  ParseBoolPipe,
  ParseArrayPipe,
  ParseUUIDPipe,
  ParseEnumPipe,
  DefaultValuePipe,
} from '@nestjs/common';
```

## Using Built-in Pipes

### Parameter Transformation

```typescript
@Controller('users')
export class UsersController {
  // Parse string to integer
  @Get(':id')
  findOne(@Param('id', ParseIntPipe) id: number) {
    return this.usersService.findOne(id);
  }

  // Parse to UUID with version
  @Get('uuid/:id')
  findByUuid(@Param('id', new ParseUUIDPipe({ version: '4' })) id: string) {
    return this.usersService.findByUuid(id);
  }

  // Default values for query params
  @Get()
  findAll(
    @Query('page', new DefaultValuePipe(1), ParseIntPipe) page: number,
    @Query('limit', new DefaultValuePipe(10), ParseIntPipe) limit: number,
  ) {
    return this.usersService.findAll({ page, limit });
  }

  // Parse enum values
  @Get('status/:status')
  findByStatus(@Param('status', new ParseEnumPipe(UserStatus)) status: UserStatus) {
    return this.usersService.findByStatus(status);
  }
}
```

## Custom Pipes

### Transformation Pipe

```typescript
@Injectable()
export class TrimPipe implements PipeTransform {
  transform(value: any) {
    if (typeof value === 'string') {
      return value.trim();
    }
    if (typeof value === 'object' && value !== null) {
      return this.trimObject(value);
    }
    return value;
  }

  private trimObject(obj: Record<string, any>) {
    const result: Record<string, any> = {};
    for (const [key, value] of Object.entries(obj)) {
      result[key] = typeof value === 'string' ? value.trim() : value;
    }
    return result;
  }
}
```

### Validation Pipe

```typescript
@Injectable()
export class FileValidationPipe implements PipeTransform {
  constructor(
    private allowedTypes: string[],
    private maxSize: number,
  ) {}

  transform(file: Express.Multer.File) {
    if (!file) {
      throw new BadRequestException('File is required');
    }

    if (!this.allowedTypes.includes(file.mimetype)) {
      throw new BadRequestException(
        `File type must be one of: ${this.allowedTypes.join(', ')}`,
      );
    }

    if (file.size > this.maxSize) {
      throw new BadRequestException(
        `File size must be less than ${this.maxSize / 1024 / 1024}MB`,
      );
    }

    return file;
  }
}

// Usage
@Post('upload')
uploadFile(
  @UploadedFile(
    new FileValidationPipe(['image/jpeg', 'image/png'], 5 * 1024 * 1024),
  )
  file: Express.Multer.File,
) {
  return { filename: file.filename };
}
```

## Global Validation Pipe

The most common use of pipes is global validation:

```typescript
// main.ts
app.useGlobalPipes(
  new ValidationPipe({
    whitelist: true,        // Strip unknown properties
    forbidNonWhitelisted: true, // Error on unknown properties
    transform: true,        // Auto-transform to DTO types
    transformOptions: {
      enableImplicitConversion: true,
    },
  }),
);
```

## Pipe Execution Order

Pipes are applied to parameters in order. When multiple pipes are chained:

```typescript
@Query('value', PipeA, PipeB, PipeC) value: string
// Execution: PipeA → PipeB → PipeC → handler
```
