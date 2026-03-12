from dotenv import load_dotenv
load_dotenv()
from llm.agents.agent import create_agent, run_agent
agent = create_agent()
result = run_agent(agent, "27살인데 월세 지원 받을 수 있어요?", verbose=True)
print(result["response"].message)
