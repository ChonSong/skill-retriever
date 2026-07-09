# Agent Evaluation

Testing agents, LLM-as-Judge, metrics, and evaluation strategies.

## Evaluation Metrics

### Quality Metrics
- Task completion rate
- Output correctness
- Code quality
- Test pass rate

### Performance Metrics
- Token usage
- Response time
- Cost per task
- Cache hit rate

### Reliability Metrics
- Error rate
- Retry rate
- Failure recovery
- Consistency

## LLM-as-Judge

### Pattern
- Use LLM to evaluate agent outputs
- Structured evaluation criteria
- Consistent scoring
- Automated assessment

### Benefits
- Scalable evaluation
- Consistent criteria
- Fast feedback
- Cost-effective

### Implementation
- Define evaluation criteria
- Create evaluation prompts
- Run evaluations
- Aggregate results

## Probe-Based Evaluation

### Concept
- Test specific capabilities
- Isolated evaluation
- Targeted assessment
- Identify gaps

### Types
- **Functional Probes** - Test specific functions
- **Integration Probes** - Test component interactions
- **End-to-End Probes** - Test complete workflows

## Evaluation Workflow

1. **Define criteria** - What to measure
2. **Create test cases** - Representative scenarios
3. **Run evaluations** - Execute tests
4. **Analyze results** - Identify issues
5. **Iterate** - Improve based on findings

## Best Practices

1. Test with real scenarios
2. Measure before and after changes
3. Use multiple evaluation methods
4. Track metrics over time
5. Set up automated evaluation
6. Review and refine criteria
