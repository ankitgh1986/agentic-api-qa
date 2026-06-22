from agents.execution_agent import ExecutionAgent

agent = ExecutionAgent(
    base_url="https://petstore3.swagger.io/api/v3"
)

result = agent.execute_operation(
    {
        "method": "GET",
        "path": "/pet/1"
    }
)

print(result)