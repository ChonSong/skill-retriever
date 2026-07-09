---
title: Security Best Practices
description: Secure your NestJS applications with proven security patterns
order: 5
category: security
difficulty: intermediate
estimatedTime: "30 min"
prerequisites:
  - getting-started
  - dependency-injection
---

# Security Best Practices

Security isn't optional—it's foundational. This guide covers essential security patterns for NestJS applications.

## Input Validation

**Never trust user input.** Validate everything that comes into your application.

### Using class-validator

```typescript
// dto/create-user.dto.ts
import {
  IsEmail,
  IsString,
  MinLength,
  MaxLength,
  Matches,
  IsOptional,
  IsEnum,
} from 'class-validator';
import { Transform } from 'class-transformer';

export class CreateUserDto {
  @IsEmail({}, { message: 'Invalid email format' })
  @Transform(({ value }) => value?.toLowerCase().trim())
  email: string;

  @IsString()
  @MinLength(8, { message: 'Password must be at least 8 characters' })
  @MaxLength(128, { message: 'Password too long' })
  @Matches(/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/, {
    message: 'Password must contain uppercase, lowercase, and number',
  })
  password: string;

  @IsOptional()
  @IsString()
  @MaxLength(100)
  @Transform(({ value }) => value?.trim())
  name?: string;

  @IsEnum(UserRole)
  role: UserRole;
}
```

### Enable Validation Globally

```typescript
// main.ts
import { ValidationPipe } from '@nestjs/common';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  app.useGlobalPipes(
    new ValidationPipe({
      whitelist: true,            // Strip properties not in DTO
      forbidNonWhitelisted: true, // Throw error on unknown properties
      transform: true,            // Auto-transform to DTO types
      transformOptions: {
        enableImplicitConversion: true,
      },
    }),
  );

  await app.listen(3000);
}
```

### Validate URL Parameters

```typescript
// dto/user-params.dto.ts
import { IsUUID } from 'class-validator';

export class UserParamsDto {
  @IsUUID('4', { message: 'Invalid user ID format' })
  id: string;
}

// users.controller.ts
@Controller('users')
export class UsersController {
  @Get(':id')
  findOne(@Param() params: UserParamsDto) {
    return this.usersService.findById(params.id);
  }
}
```

## Authentication

### JWT Authentication

```typescript
// auth/auth.module.ts
@Module({
  imports: [
    JwtModule.registerAsync({
      inject: [ConfigService],
      useFactory: (config: ConfigService) => ({
        secret: config.get('JWT_SECRET'),
        signOptions: {
          expiresIn: '15m',      // Short-lived access tokens
          issuer: 'your-app',
          audience: 'your-app',
        },
      }),
    }),
  ],
  providers: [AuthService, JwtStrategy],
  exports: [AuthService],
})
export class AuthModule {}
```

### JWT Strategy

```typescript
// auth/jwt.strategy.ts
@Injectable()
export class JwtStrategy extends PassportStrategy(Strategy) {
  constructor(
    private configService: ConfigService,
    private usersService: UsersService,
  ) {
    super({
      jwtFromRequest: ExtractJwt.fromAuthHeaderAsBearerToken(),
      ignoreExpiration: false,
      secretOrKey: configService.get('JWT_SECRET'),
      issuer: 'your-app',
      audience: 'your-app',
    });
  }

  async validate(payload: JwtPayload) {
    // Verify user still exists and is active
    const user = await this.usersService.findById(payload.sub);

    if (!user || !user.isActive) {
      throw new UnauthorizedException('User not found or inactive');
    }

    return { userId: payload.sub, email: payload.email, roles: payload.roles };
  }
}
```

### Refresh Token Pattern

```typescript
// auth/auth.service.ts
@Injectable()
export class AuthService {
  constructor(
    private jwtService: JwtService,
    private usersService: UsersService,
    private refreshTokenRepository: RefreshTokenRepository,
  ) {}

  async login(user: User) {
    const payload = { sub: user.id, email: user.email, roles: user.roles };

    // Short-lived access token
    const accessToken = this.jwtService.sign(payload, { expiresIn: '15m' });

    // Long-lived refresh token (stored in DB)
    const refreshToken = await this.createRefreshToken(user.id);

    return { accessToken, refreshToken };
  }

  async refreshTokens(refreshToken: string) {
    const storedToken = await this.refreshTokenRepository.findByToken(refreshToken);

    if (!storedToken || storedToken.isRevoked || storedToken.expiresAt < new Date()) {
      throw new UnauthorizedException('Invalid refresh token');
    }

    const user = await this.usersService.findById(storedToken.userId);

    // Revoke old token and issue new pair
    await this.refreshTokenRepository.revoke(refreshToken);

    return this.login(user);
  }

  private async createRefreshToken(userId: string): Promise<string> {
    const token = crypto.randomBytes(64).toString('hex');
    const expiresAt = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000); // 7 days

    await this.refreshTokenRepository.create({
      token,
      userId,
      expiresAt,
    });

    return token;
  }
}
```

## Authorization with Guards

### Role-Based Access Control (RBAC)

```typescript
// decorators/roles.decorator.ts
import { SetMetadata } from '@nestjs/common';

export const ROLES_KEY = 'roles';
export const Roles = (...roles: Role[]) => SetMetadata(ROLES_KEY, roles);

// guards/roles.guard.ts
@Injectable()
export class RolesGuard implements CanActivate {
  constructor(private reflector: Reflector) {}

  canActivate(context: ExecutionContext): boolean {
    const requiredRoles = this.reflector.getAllAndOverride<Role[]>(ROLES_KEY, [
      context.getHandler(),
      context.getClass(),
    ]);

    if (!requiredRoles) {
      return true; // No roles required
    }

    const { user } = context.switchToHttp().getRequest();
    return requiredRoles.some(role => user.roles?.includes(role));
  }
}

// Usage
@Controller('admin')
@UseGuards(JwtAuthGuard, RolesGuard)
export class AdminController {
  @Get('users')
  @Roles(Role.ADMIN)
  findAllUsers() {
    return this.usersService.findAll();
  }

  @Delete('users/:id')
  @Roles(Role.SUPER_ADMIN)
  deleteUser(@Param('id') id: string) {
    return this.usersService.delete(id);
  }
}
```

### Resource-Based Authorization

```typescript
// guards/resource-owner.guard.ts
@Injectable()
export class ResourceOwnerGuard implements CanActivate {
  constructor(
    private reflector: Reflector,
    private moduleRef: ModuleRef,
  ) {}

  async canActivate(context: ExecutionContext): Promise<boolean> {
    const request = context.switchToHttp().getRequest();
    const user = request.user;

    // Get the resource service from metadata
    const resourceService = this.reflector.get<Type>(
      'resourceService',
      context.getHandler(),
    );

    if (!resourceService) {
      return true;
    }

    const service = this.moduleRef.get(resourceService, { strict: false });
    const resourceId = request.params.id;

    const resource = await service.findById(resourceId);

    if (!resource) {
      throw new NotFoundException();
    }

    // Check ownership
    return resource.userId === user.userId || user.roles.includes(Role.ADMIN);
  }
}

// decorator
export const CheckOwnership = (service: Type) =>
  SetMetadata('resourceService', service);

// Usage
@Controller('posts')
@UseGuards(JwtAuthGuard, ResourceOwnerGuard)
export class PostsController {
  @Put(':id')
  @CheckOwnership(PostsService)
  update(@Param('id') id: string, @Body() dto: UpdatePostDto) {
    return this.postsService.update(id, dto);
  }
}
```

## Output Sanitization

### Exclude Sensitive Fields

```typescript
// entities/user.entity.ts
import { Exclude, Expose } from 'class-transformer';

export class User {
  @Expose()
  id: string;

  @Expose()
  email: string;

  @Exclude()
  password: string;

  @Exclude()
  refreshTokens: string[];

  @Expose()
  createdAt: Date;
}

// Enable serialization in main.ts
app.useGlobalInterceptors(new ClassSerializerInterceptor(app.get(Reflector)));
```

### Response DTOs

```typescript
// dto/user-response.dto.ts
export class UserResponseDto {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  createdAt: Date;

  constructor(user: User) {
    this.id = user.id;
    this.email = user.email;
    this.name = user.name;
    this.role = user.role;
    this.createdAt = user.createdAt;
    // Explicitly exclude password, tokens, etc.
  }
}

// Usage in controller
@Get(':id')
async findOne(@Param('id') id: string) {
  const user = await this.usersService.findById(id);
  return new UserResponseDto(user);
}
```

## Rate Limiting

```typescript
// main.ts
import { ThrottlerModule, ThrottlerGuard } from '@nestjs/throttler';

@Module({
  imports: [
    ThrottlerModule.forRoot([
      {
        name: 'short',
        ttl: 1000,      // 1 second
        limit: 3,       // 3 requests
      },
      {
        name: 'medium',
        ttl: 10000,     // 10 seconds
        limit: 20,      // 20 requests
      },
      {
        name: 'long',
        ttl: 60000,     // 1 minute
        limit: 100,     // 100 requests
      },
    ]),
  ],
  providers: [
    {
      provide: APP_GUARD,
      useClass: ThrottlerGuard,
    },
  ],
})
export class AppModule {}

// Custom limits per route
@Controller('auth')
export class AuthController {
  @Post('login')
  @Throttle({ short: { limit: 5, ttl: 60000 } }) // 5 attempts per minute
  login(@Body() dto: LoginDto) {
    return this.authService.login(dto);
  }
}
```

## Security Headers

```typescript
// main.ts
import helmet from 'helmet';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  // Security headers
  app.use(helmet());

  // CORS configuration
  app.enableCors({
    origin: process.env.ALLOWED_ORIGINS?.split(',') || ['http://localhost:3000'],
    credentials: true,
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'],
    allowedHeaders: ['Content-Type', 'Authorization'],
  });

  await app.listen(3000);
}
```

## SQL Injection Prevention

Always use parameterized queries:

```typescript
// ❌ Vulnerable to SQL injection
async findByEmail(email: string) {
  return this.dataSource.query(
    `SELECT * FROM users WHERE email = '${email}'`
  );
}

// ✅ Safe - parameterized query
async findByEmail(email: string) {
  return this.dataSource.query(
    'SELECT * FROM users WHERE email = $1',
    [email]
  );
}

// ✅ Safe - using TypeORM repository
async findByEmail(email: string) {
  return this.usersRepository.findOne({ where: { email } });
}

// ✅ Safe - using QueryBuilder with parameters
async findByEmail(email: string) {
  return this.usersRepository
    .createQueryBuilder('user')
    .where('user.email = :email', { email })
    .getOne();
}
```

## Summary

| Security Measure | Implementation |
|-----------------|----------------|
| Input validation | class-validator + ValidationPipe |
| Authentication | JWT with refresh tokens |
| Authorization | Guards + decorators |
| Output sanitization | class-transformer + DTOs |
| Rate limiting | @nestjs/throttler |
| Security headers | helmet |
| SQL injection | Parameterized queries |

## Security Checklist

- [ ] All input validated with class-validator
- [ ] Passwords hashed with bcrypt (cost factor ≥ 10)
- [ ] JWT tokens short-lived (15 min max)
- [ ] Refresh tokens stored securely
- [ ] Sensitive data excluded from responses
- [ ] Rate limiting on auth endpoints
- [ ] Security headers configured
- [ ] CORS properly configured
- [ ] SQL injection prevented
- [ ] Secrets in environment variables

## Additional Reading

- [Validate All Input](/rules/security-validate-all-input) - Detailed validation patterns
- [Use Guards](/rules/security-use-guards) - Authorization patterns
- [Rate Limiting](/rules/security-rate-limiting) - Protect against abuse
