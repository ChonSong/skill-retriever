---
title: Request Validation
description: Validate incoming requests with class-validator and transform data with class-transformer
difficulty: beginner
category: patterns
estimatedTime: 15 min
order: 7
prerequisites:
  - getting-started
---

# Request Validation

Proper validation protects your application from malformed data and security vulnerabilities. NestJS integrates seamlessly with class-validator and class-transformer.

## Setting Up Validation

Install the required packages:

```bash
npm install class-validator class-transformer
```

Enable global validation in your main.ts:

```typescript
// main.ts
import { ValidationPipe } from '@nestjs/common';
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  app.useGlobalPipes(
    new ValidationPipe({
      whitelist: true,           // Strip non-whitelisted properties
      forbidNonWhitelisted: true, // Throw error on extra properties
      transform: true,           // Auto-transform payloads to DTO types
      transformOptions: {
        enableImplicitConversion: true, // Convert primitive types
      },
    }),
  );

  await app.listen(3000);
}
bootstrap();
```

## Creating DTOs with Validation

### Basic DTO

```typescript
// dto/create-user.dto.ts
import {
  IsEmail,
  IsString,
  IsNotEmpty,
  MinLength,
  MaxLength,
  Matches,
} from 'class-validator';

export class CreateUserDto {
  @IsEmail({}, { message: 'Please provide a valid email address' })
  email: string;

  @IsString()
  @IsNotEmpty()
  @MinLength(2)
  @MaxLength(50)
  name: string;

  @IsString()
  @MinLength(8, { message: 'Password must be at least 8 characters' })
  @Matches(/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/, {
    message: 'Password must contain uppercase, lowercase, and number',
  })
  password: string;
}
```

### Nested Object Validation

```typescript
// dto/create-order.dto.ts
import {
  IsArray,
  IsInt,
  IsPositive,
  IsString,
  IsUUID,
  Min,
  ValidateNested,
} from 'class-validator';
import { Type } from 'class-transformer';

class OrderItemDto {
  @IsUUID()
  productId: string;

  @IsInt()
  @IsPositive()
  quantity: number;
}

class ShippingAddressDto {
  @IsString()
  @IsNotEmpty()
  street: string;

  @IsString()
  @IsNotEmpty()
  city: string;

  @IsString()
  @IsNotEmpty()
  postalCode: string;

  @IsString()
  @IsNotEmpty()
  country: string;
}

export class CreateOrderDto {
  @IsArray()
  @ValidateNested({ each: true })
  @Type(() => OrderItemDto)
  items: OrderItemDto[];

  @ValidateNested()
  @Type(() => ShippingAddressDto)
  shippingAddress: ShippingAddressDto;

  @IsString()
  @IsOptional()
  notes?: string;
}
```

### Conditional Validation

```typescript
// dto/payment.dto.ts
import {
  IsEnum,
  IsString,
  ValidateIf,
  IsCreditCard,
  IsIBAN,
} from 'class-validator';

enum PaymentMethod {
  CARD = 'card',
  BANK_TRANSFER = 'bank_transfer',
  PAYPAL = 'paypal',
}

export class PaymentDto {
  @IsEnum(PaymentMethod)
  method: PaymentMethod;

  // Only validate card number if payment method is card
  @ValidateIf((o) => o.method === PaymentMethod.CARD)
  @IsCreditCard()
  cardNumber?: string;

  // Only validate IBAN if payment method is bank transfer
  @ValidateIf((o) => o.method === PaymentMethod.BANK_TRANSFER)
  @IsIBAN()
  iban?: string;

  // Only validate email if payment method is PayPal
  @ValidateIf((o) => o.method === PaymentMethod.PAYPAL)
  @IsEmail()
  paypalEmail?: string;
}
```

## Query Parameter Validation

```typescript
// dto/pagination.dto.ts
import { IsInt, IsOptional, Min, Max } from 'class-validator';
import { Type } from 'class-transformer';

export class PaginationDto {
  @IsOptional()
  @Type(() => Number)
  @IsInt()
  @Min(1)
  page?: number = 1;

  @IsOptional()
  @Type(() => Number)
  @IsInt()
  @Min(1)
  @Max(100)
  limit?: number = 10;
}

// dto/filter-users.dto.ts
import { IsOptional, IsString, IsEnum, IsBoolean } from 'class-validator';
import { Transform, Type } from 'class-transformer';

enum UserRole {
  ADMIN = 'admin',
  USER = 'user',
  MODERATOR = 'moderator',
}

export class FilterUsersDto extends PaginationDto {
  @IsOptional()
  @IsString()
  search?: string;

  @IsOptional()
  @IsEnum(UserRole)
  role?: UserRole;

  @IsOptional()
  @Transform(({ value }) => value === 'true')
  @IsBoolean()
  isActive?: boolean;

  @IsOptional()
  @Type(() => Date)
  createdAfter?: Date;
}
```

Using in a controller:

```typescript
// users.controller.ts
import { Controller, Get, Query } from '@nestjs/common';
import { FilterUsersDto } from './dto/filter-users.dto';

@Controller('users')
export class UsersController {
  @Get()
  findAll(@Query() filters: FilterUsersDto) {
    // filters is fully typed and validated
    console.log(filters.page);      // number (default: 1)
    console.log(filters.isActive);  // boolean or undefined
    return this.usersService.findAll(filters);
  }
}
```

## Custom Validators

### Simple Custom Validator

```typescript
// validators/is-unique-email.validator.ts
import {
  registerDecorator,
  ValidationOptions,
  ValidatorConstraint,
  ValidatorConstraintInterface,
  ValidationArguments,
} from 'class-validator';
import { Injectable } from '@nestjs/common';
import { UsersService } from '../users/users.service';

@Injectable()
@ValidatorConstraint({ async: true })
export class IsUniqueEmailConstraint implements ValidatorConstraintInterface {
  constructor(private usersService: UsersService) {}

  async validate(email: string, args: ValidationArguments) {
    const user = await this.usersService.findByEmail(email);
    return !user; // Valid if user doesn't exist
  }

  defaultMessage(args: ValidationArguments) {
    return 'Email $value is already registered';
  }
}

export function IsUniqueEmail(validationOptions?: ValidationOptions) {
  return function (object: object, propertyName: string) {
    registerDecorator({
      target: object.constructor,
      propertyName: propertyName,
      options: validationOptions,
      constraints: [],
      validator: IsUniqueEmailConstraint,
    });
  };
}
```

Register the constraint in your module:

```typescript
// users.module.ts
import { Module } from '@nestjs/common';
import { IsUniqueEmailConstraint } from './validators/is-unique-email.validator';

@Module({
  providers: [UsersService, IsUniqueEmailConstraint],
})
export class UsersModule {}
```

Use in your DTO:

```typescript
// dto/create-user.dto.ts
export class CreateUserDto {
  @IsEmail()
  @IsUniqueEmail({ message: 'This email is already taken' })
  email: string;
}
```

### Cross-Field Validation

```typescript
// validators/match.validator.ts
import {
  registerDecorator,
  ValidationOptions,
  ValidationArguments,
} from 'class-validator';

export function Match(property: string, validationOptions?: ValidationOptions) {
  return function (object: object, propertyName: string) {
    registerDecorator({
      name: 'match',
      target: object.constructor,
      propertyName: propertyName,
      constraints: [property],
      options: validationOptions,
      validator: {
        validate(value: any, args: ValidationArguments) {
          const [relatedPropertyName] = args.constraints;
          const relatedValue = (args.object as any)[relatedPropertyName];
          return value === relatedValue;
        },
        defaultMessage(args: ValidationArguments) {
          const [relatedPropertyName] = args.constraints;
          return `${args.property} must match ${relatedPropertyName}`;
        },
      },
    });
  };
}
```

Use for password confirmation:

```typescript
// dto/register.dto.ts
export class RegisterDto {
  @IsEmail()
  email: string;

  @IsString()
  @MinLength(8)
  password: string;

  @IsString()
  @Match('password', { message: 'Passwords do not match' })
  confirmPassword: string;
}
```

## Data Transformation

### Automatic Transformation

```typescript
// dto/update-profile.dto.ts
import { Transform, Type } from 'class-transformer';
import { IsString, IsOptional, IsDate } from 'class-validator';

export class UpdateProfileDto {
  @IsOptional()
  @IsString()
  @Transform(({ value }) => value?.trim()) // Trim whitespace
  name?: string;

  @IsOptional()
  @IsString()
  @Transform(({ value }) => value?.toLowerCase()) // Lowercase
  username?: string;

  @IsOptional()
  @Type(() => Date)
  @IsDate()
  birthDate?: Date;
}
```

### Sanitizing Input

```typescript
// dto/create-post.dto.ts
import { Transform } from 'class-transformer';
import { IsString, MaxLength } from 'class-validator';
import sanitizeHtml from 'sanitize-html';

export class CreatePostDto {
  @IsString()
  @MaxLength(200)
  @Transform(({ value }) => value?.trim())
  title: string;

  @IsString()
  @Transform(({ value }) =>
    sanitizeHtml(value, {
      allowedTags: ['b', 'i', 'em', 'strong', 'a', 'p', 'br'],
      allowedAttributes: {
        a: ['href'],
      },
    }),
  )
  content: string;
}
```

## Partial Updates with PartialType

```typescript
// dto/update-user.dto.ts
import { PartialType } from '@nestjs/mapped-types';
import { CreateUserDto } from './create-user.dto';

// All properties from CreateUserDto become optional
export class UpdateUserDto extends PartialType(CreateUserDto) {}
```

## Error Response Customization

Create a custom validation pipe for better error responses:

```typescript
// pipes/custom-validation.pipe.ts
import {
  BadRequestException,
  ValidationPipe,
  ValidationError,
} from '@nestjs/common';

export class CustomValidationPipe extends ValidationPipe {
  constructor() {
    super({
      whitelist: true,
      forbidNonWhitelisted: true,
      transform: true,
      exceptionFactory: (errors: ValidationError[]) => {
        const formattedErrors = errors.reduce((acc, error) => {
          const constraints = error.constraints;
          if (constraints) {
            acc[error.property] = Object.values(constraints);
          }
          // Handle nested errors
          if (error.children?.length) {
            acc[error.property] = this.formatNestedErrors(error.children);
          }
          return acc;
        }, {} as Record<string, any>);

        return new BadRequestException({
          statusCode: 400,
          message: 'Validation failed',
          errors: formattedErrors,
        });
      },
    });
  }

  private formatNestedErrors(errors: ValidationError[]): Record<string, any> {
    return errors.reduce((acc, error) => {
      if (error.constraints) {
        acc[error.property] = Object.values(error.constraints);
      }
      if (error.children?.length) {
        acc[error.property] = this.formatNestedErrors(error.children);
      }
      return acc;
    }, {} as Record<string, any>);
  }
}
```

Example error response:

```json
{
  "statusCode": 400,
  "message": "Validation failed",
  "errors": {
    "email": ["Please provide a valid email address"],
    "password": [
      "Password must be at least 8 characters",
      "Password must contain uppercase, lowercase, and number"
    ],
    "shippingAddress": {
      "postalCode": ["postalCode must be a string"]
    }
  }
}
```

## Summary

- Enable **global validation** with `ValidationPipe` in main.ts
- Use **class-validator decorators** for declarative validation
- Use **class-transformer** for automatic type conversion
- Create **custom validators** for business-specific rules
- **Whitelist** properties to prevent mass assignment vulnerabilities
- Use **PartialType** for update DTOs
- Customize **error responses** for better API UX
