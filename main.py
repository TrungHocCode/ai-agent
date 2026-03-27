from agents.multi_agent import MultiAgentGraph
from agents.agent_registry import AGENT_REGISTRY


if __name__ == "__main__":
    graph = MultiAgentGraph(registry=AGENT_REGISTRY)
    print("Configured workers and tools:")
    for name, agent in graph.workers.items():
        tool_list = [t.name for t in agent.tools]
        print(f" - {name}: {tool_list}")
    print("\nYou can now type a query.")
    while True:
        try:
            query = input("\nYou: ").strip()
            if query.lower() in ["exit", "quit", "bye"]:
                
                print("Goodbye!")
                break
            if not query:
                continue
            result = graph.invoke(query)
            messages = result.get("messages", [])
            print(f"\nAI: {messages[-1] if messages else 'No response'}")
        except KeyboardInterrupt:
            print("\nGoodbye!")
            print(messages)
            break
        except Exception as e:
            print(f"Error: {str(e)}")