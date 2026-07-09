---
title: Custom Decorators
description: Create reusable decorators for cleaner, more expressive code
category: core
relatedRules:
  - create-custom-decorators
  - use-decorator-composition
---

# Custom Decorators

Decorators are a powerful TypeScript feature that NestJS leverages extensively. You can create custom decorators to reduce boilerplate and make code more expressive.

## Parameter Decorators

Extract data from the request:

```typescript
// decorators/current-user.decorator.ts
import { createParamDecorator, ExecutionContext } from '@nestjs/common';

export const CurrentUser = createParamDecorator(
  (data: keyof User | undefined, ctx: ExecutionContext) => {
    const request = ctx.switchToHttp().getRequest();
    const user = request.user;

    return data ? user?.[data] : user;
  },
);

// Usage in controller
@Get('profile')
getProfile(@CurrentUser() user: User) {
  return user;
}

@Get('email')
getEmail(@CurrentUser('email') email: string) {
  return { email };
}
```

### Request Metadata Decorator

```typescript
// decorators/request-id.decorator.ts
export const RequestId = createParamDecorator(
  (data: unknown, ctx: ExecutionContext) => {
    const request = ctx.switchToHttp().getRequest();
    return request.headers['x-request-id'] || request.id;
  },
);

// Usage
@Post()
create(@RequestId() requestId: string, @Body() dto: CreateDto) {
  this.logger.log(`Processing request ${requestId}`);
}
```

## Metadata Decorators

Set metadata for guards, interceptors, or other handlers:

```typescript
// decorators/roles.decorator.ts
import { SetMetadata } from '@nestjs/common';

export const ROLES_KEY = 'roles';
export const Roles = (...roles: string[]) => SetMetadata(ROLES_KEY, roles);

// decorators/public.decorator.ts
export const IS_PUBLIC_KEY = 'isPublic';
export const Public = () => SetMetadata(IS_PUBLIC_KEY, true);

// Usage
@Roles('admin', 'moderator')
@Get('admin')
adminOnly() {}

@Public()
@Get('health')
healthCheck() {}
```

### Reading Metadata in Guards

```typescript
// guards/roles.guard.ts
@Injectable()
export class RolesGuard implements CanActivate {
  constructor(private reflector: Reflector) {}

  canActivate(context: ExecutionContext): boolean {
    const requiredRoles = this.reflector.getAllAndOverride<string[]>(
      ROLES_KEY,
      [context.getHandler(), context.getClass()],
    );

    if (!requiredRoles) {
      return true;
    }

    const { user } = context.switchToHttp().getRequest();
    return requiredRoles.some((role) => user.roles?.includes(role));
  }
}
```

## Decorator Composition

Combine multiple decorators into one:

```typescript
// decorators/auth.decorator.ts
import { applyDecorators, UseGuards } from '@nestjs/common';
import { ApiBearerAuth, ApiUnauthorizedResponse } from '@nestjs/swagger';

export function Auth(...roles: string[]) {
  return applyDecorators(
    SetMetadata(ROLES_KEY, roles),
    UseGuards(JwtAuthGuard, RolesGuard),
    ApiBearerAuth(),
    ApiUnauthorizedResponse({ description: 'Unauthorized' }),
  );
}

// Usage - replaces 4 decorators with 1
@Auth('admin')
@Get('admin/users')
getAllUsers() {}
```

### API Endpoint Decorator

```typescript
// decorators/api-endpoint.decorator.ts
export function ApiEndpoint(options: {
  summary: string;
  roles?: string[];
  isPublic?: boolean;
}) {
  const decorators = [ApiOperation({ summary: options.summary })];

  if (options.isPublic) {
    decorators.push(Public());
  } else {
    decorators.push(UseGuards(JwtAuthGuard));
    if (options.roles?.length) {
      decorators.push(Roles(...options.roles));
      decorators.push(UseGuards(RolesGuard));
    }
  }

  return applyDecorators(...decorators);
}

// Usage
@ApiEndpoint({ summary: 'Get user profile', roles: ['user'] })
@Get('profile')
getProfile() {}
```

## Class Decorators

Create decorators that apply to entire classes:

```typescript
// decorators/api-controller.decorator.ts
export function ApiController(prefix: string) {
  return applyDecorators(
    Controller(prefix),
    ApiTags(prefix),
    UseInterceptors(LoggingInterceptor),
  );
}

// Usage
@ApiController('users')
export class UsersController {}
```

## Method Decorators

Create method-level decorators:

```typescript
// decorators/log-execution.decorator.ts
export function LogExecution() {
  return function (
    target: any,
    propertyKey: string,
    descriptor: PropertyDescriptor,
  ) {
    const originalMethod = descriptor.value;

    descriptor.value = async function (...args: any[]) {
      const start = Date.now();
      console.log(`Executing ${propertyKey}...`);

      const result = await originalMethod.apply(this, args);

      console.log(`${propertyKey} completed in ${Date.now() - start}ms`);
      return result;
    };

    return descriptor;
  };
}

// Usage
@LogExecution()
async processOrder(orderId: string) {
  // Method execution is automatically logged
}
```

## Best Practices

1. **Keep decorators focused** - Each decorator should do one thing
2. **Use composition** - Combine simple decorators into complex ones
3. **Document usage** - Add JSDoc comments to custom decorators
4. **Type safety** - Use generics where appropriate
5. **Avoid side effects** - Decorators should be predictable
