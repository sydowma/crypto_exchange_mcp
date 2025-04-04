from mcp.server import Server
import mcp.types as types

# Define available prompts
PROMPTS = {
    "last-price": types.Prompt(
        name="last-price",
        description="Get the last price of a symbol",
        arguments=[
            types.PromptArgument(
                name="symbol",
                description="The symbol to get the last price of",
                required=True
            )
        ],
    )
}


async def list_prompts() -> list[types.Prompt]:
    return list(PROMPTS.values())

async def get_prompt(
    name: str, arguments: dict[str, str] | None = None
) -> types.GetPromptResult:
    if name not in PROMPTS:
        raise ValueError(f"Prompt not found: {name}")

    if name == "last-price":
        symbol = arguments.get("symbol") if arguments else ""
        return types.GetPromptResult(
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=f"Get the last price of {symbol}"
                    )
                )
            ]
        )

    raise ValueError("Prompt implementation not found")