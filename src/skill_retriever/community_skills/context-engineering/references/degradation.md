# Context Degradation

Failure patterns when context exceeds optimal size or structure.

## Lost-in-the-Middle

### Problem
Information in the middle of context receives less attention than beginning/end.

### Symptoms
- Agent misses information in middle sections
- Inconsistent behavior with same information
- Better performance with shorter context

### Solutions
- Place critical info at beginning/end
- Use progressive disclosure
- Split large contexts across sub-agents
- Summarize middle sections

## Context Poisoning

### Problem
Malicious or low-quality content degrades performance.

### Symptoms
- Agent follows incorrect instructions from context
- Performance degrades with more context
- Inconsistent outputs

### Solutions
- Validate context sources
- Filter low-quality content
- Use trusted sources only
- Monitor for anomalies

## Attention Dilution

### Problem
Too much information dilutes attention to critical content.

### Symptoms
- Agent misses important details
- Performance degrades with more context
- Inconsistent focus

### Solutions
- Curate high-signal content
- Remove redundant information
- Use progressive disclosure
- Focus on task-relevant content

## Token Limit Exceeded

### Problem
Context exceeds model's token limit.

### Symptoms
- Truncation of context
- Missing information
- Errors or failures

### Solutions
- Implement compaction at 70-80% utilization
- Use summarization
- Split across multiple requests
- Use sub-agents for isolation

## Detection

### Warning Signs
- Token utilization >70%
- Performance degradation
- Missing information
- Inconsistent outputs

### Monitoring
- Track token usage
- Monitor performance metrics
- Detect degradation patterns
- Set up alerts
