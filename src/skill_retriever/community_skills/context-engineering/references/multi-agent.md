# Multi-Agent Patterns

Coordination patterns, context isolation, and multi-agent architectures.

## Context Isolation

### Benefits
- Prevent context degradation
- Enable parallel processing
- Isolate failures
- Reduce token usage per agent

### Patterns
- **Task Partitioning** - Split work by task
- **Domain Partitioning** - Split by domain
- **Pipeline Partitioning** - Sequential stages

## Coordination Patterns

### Orchestration
- Central coordinator
- Manages workflow
- Coordinates sub-agents
- Handles failures

### Choreography
- Decentralized coordination
- Event-driven communication
- Self-organizing
- Loose coupling

## Cost Considerations

### Multi-Agent Cost
- ~15x single agent baseline
- Each agent has own context
- Parallel execution overhead
- Coordination complexity

### When to Use
- Large, independent tasks
- Parallelizable work
- Context limits reached
- Performance critical

## Communication Patterns

### Message Passing
- Direct communication
- Event-driven
- Request/response
- Async messaging

### Shared State
- External storage
- Database
- Cache
- File system

## Best Practices

1. Use sub-agents for context isolation, not role-play
2. Partition by task, not by role
3. Minimize inter-agent communication
4. Use external storage for shared state
5. Monitor costs and performance
6. Start with single agent, split when needed
