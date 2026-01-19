import asyncio
import os
from pathlib import Path
from typing import Any, Dict

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_aws import ChatBedrockConverse
from langchain_mcp_adapters import MultiServerMCPClient

from rp_personality import RP_SYSTEM


def _extract_prompt_text(prompt_result: Any) -> str:
    if isinstance(prompt_result, dict):
        if "messages" in prompt_result:
            parts = []
            for message in prompt_result["messages"]:
                role = message.get("role", "system")
                content = message.get("content", "")
                parts.append(f"[{role}] {content}".strip())
            return "\n".join(parts)
        if "content" in prompt_result:
            return str(prompt_result["content"])
    return str(prompt_result)


def _build_mcp_config() -> Dict[str, Dict[str, Any]]:
    server_path = Path(__file__).resolve().parents[1] / "server" / "ps_mcp_server.py"
    return {
        "ps": {
            "transport": "stdio",
            "command": "python",
            "args": [str(server_path)],
        }
    }


async def main() -> None:
    model_id = os.environ.get("BEDROCK_MODEL_ID")
    region = os.environ.get("AWS_REGION")
    if not model_id or not region:
        raise RuntimeError("BEDROCK_MODEL_ID and AWS_REGION must be set in the environment")

    llm = ChatBedrockConverse(
        model_id=model_id,
        region_name=region,
    )

    client = MultiServerMCPClient(_build_mcp_config())
    async with client:
        tools = await client.get_tools()
        skill_prompt = await client.get_prompt(
            "ps",
            "asset_allocation_report_skill",
            arguments={"report_title": "My Portfolio Asset Allocation"},
        )

        skill_prompt_text = _extract_prompt_text(skill_prompt)
        print("Loaded skill prompt: asset_allocation_report_skill")
        print(skill_prompt_text)

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", RP_SYSTEM),
                ("system", skill_prompt_text),
                ("human", "{input}"),
            ]
        )

        agent = create_tool_calling_agent(llm, tools, prompt)
        executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            return_intermediate_steps=True,
        )

        result = await executor.ainvoke(
            {"input": "make me a report for my portfolio on asset allocation"}
        )
        print("\nFinal Answer:")
        print(result.get("output"))

        print("\nTool Call Logs:")
        for action, observation in result.get("intermediate_steps", []):
            tool_name = getattr(action, "tool", "unknown")
            tool_input = getattr(action, "tool_input", "")
            print(f"Tool call: {tool_name} | input: {tool_input}")
            print(f"Observation: {observation}")


if __name__ == "__main__":
    asyncio.run(main())
