---
title: Guards
description: Implement authentication and authorization with guards
order: 3
category: security
relatedRules:
  - security-use-guards
  - security-auth-jwt
---

# Guards

Guards determine whether a request should be handled by a route handler. They're perfect for authentication and authorization.

## How Guards Work

Guards implement the `CanActivate` interface:

```typescript
import { Injectable, CanActivate, ExecutionContext } from '@nestjs/common';

@Injectable()
export class AuthGuard implements CanActivate {
  canActivate(context: ExecutionContext): boolean {
    const request = context.switchToHttp().getRequest();
    return this.validateRequest(request);
  }

  private validateRequest(request: Request): boolean {
    // Return true to allow, false to deny
    return !!request.headers.authorization;
  }
}
```

## Execution Order

Guards run in this order:

1. Global guards
2. Controller guards
3. Route guards

```typescript
// Global (runs first)
app.useGlobalGuards(new GlobalGuard());

// Controller level (runs second)
@Controller('users')
@UseGuards(ControllerGuard)
export class UsersController {
  // Route level (runs third)
  @Get()
  @UseGuards(RouteGuard)
  findAll() {}
}
```

## Common Guard Patterns

### JWT Authentication Guard

```typescript
@Injectable()
export class JwtAuthGuard extends AuthGuard('jwt') {
  canActivate(context: ExecutionContext) {
    return super.canActivate(context);
  }

  handleRequest(err: any, user: any) {
    if (err || !user) {
      throw new UnauthorizedException('Invalid or expired token');
    }
    return user;
  }
}
```

### Role-Based Guard

```typescript
@Injectable()
export class RolesGuard implements CanActivate {
  constructor(private reflector: Reflector) {}

  canActivate(context: ExecutionContext): boolean {
    const requiredRoles = this.reflector.get<string[]>(
      'roles',
      context.getHandler(),
    );

    if (!requiredRoles) {
      return true;
    }

    const { user } = context.switchToHttp().getRequest();
    return requiredRoles.some(role => user.roles?.includes(role));
  }
}

// Usage with decorator
@Get('admin')
@Roles('admin')
@UseGuards(JwtAuthGuard, RolesGuard)
adminOnly() {}
```

### Rate Limit Guard

```typescript
@Injectable()
export class RateLimitGuard implements CanActivate {
  private requests = new Map<string, number[]>();

  canActivate(context: ExecutionContext): boolean {
    const request = context.switchToHttp().getRequest();
    const ip = request.ip;
    const now = Date.now();
    const windowMs = 60000; // 1 minute
    const maxRequests = 100;

    const timestamps = this.requests.get(ip) || [];
    const recent = timestamps.filter(t => now - t < windowMs);

    if (recent.length >= maxRequests) {
      throw new HttpException('Too many requests', HttpStatus.TOO_MANY_REQUESTS);
    }

    recent.push(now);
    this.requests.set(ip, recent);

    return true;
  }
}
```

## Guard vs Middleware vs Interceptor

| Feature | Middleware | Guard | Interceptor |
|---------|-----------|-------|-------------|
| Access to route metadata | ❌ | ✅ | ✅ |
| Can reject request | ✅ | ✅ | ✅ |
| Can transform request | ✅ | ❌ | ✅ |
| Can transform response | ❌ | ❌ | ✅ |
| Best for | Logging, CORS | Auth, permissions | Transform, cache |

## Related

- [Security Guide](/guides/security)
- [Use Guards](/rules/security-use-guards)
