from __future__ import annotations

from typing import Any, Dict

from fastmcp import FastMCP

from state import STATE

mcp = FastMCP("portfolio-reporting-demo")


def _ensure_current_workbook() -> Dict[str, Any]:
    workbook = STATE.get_current()
    if not workbook:
        return {"error": "no workbook is currently open"}
    return {"workbook": workbook}


@mcp.tool()
def create_workbook(name: str) -> Dict[str, Any]:
    workbook = STATE.create_workbook(name)
    return {"workbook_id": workbook.workbook_id, "name": workbook.name}


@mcp.tool()
def open_workbook(workbook_id: str) -> Dict[str, Any]:
    workbook = STATE.open_workbook(workbook_id)
    if not workbook:
        return {"error": f"workbook '{workbook_id}' not found"}
    return {"workbook_id": workbook.workbook_id, "name": workbook.name}


@mcp.tool()
def load_portfolio(portfolio_json: Dict[str, Any]) -> Dict[str, Any]:
    result = _ensure_current_workbook()
    if "error" in result:
        return result
    workbook = result["workbook"]
    workbook.portfolio = portfolio_json
    return {"workbook_id": workbook.workbook_id, "portfolio": workbook.portfolio}


@mcp.tool()
def add_section(section_type: str) -> Dict[str, Any]:
    result = _ensure_current_workbook()
    if "error" in result:
        return result
    workbook = result["workbook"]
    section = {"type": section_type}
    workbook.sections.append(section)
    return {"workbook_id": workbook.workbook_id, "section": section}


@mcp.tool()
def add_chart(chart_type: str, data_source: str, settings: Dict[str, Any]) -> Dict[str, Any]:
    result = _ensure_current_workbook()
    if "error" in result:
        return result
    workbook = result["workbook"]
    chart = {
        "type": chart_type,
        "data_source": data_source,
        "settings": settings,
    }
    workbook.charts.append(chart)
    return {"workbook_id": workbook.workbook_id, "chart": chart}


@mcp.tool()
def render_report(format: str) -> Dict[str, Any]:
    result = _ensure_current_workbook()
    if "error" in result:
        return result
    workbook = result["workbook"]
    artifact = f"report://{workbook.workbook_id}.{format}"
    return {"artifact": artifact}


@mcp.tool()
def show_state() -> Dict[str, Any]:
    return STATE.to_dict()


@mcp.prompt()
def asset_allocation_report_skill(report_title: str = "Asset Allocation Report") -> Dict[str, Any]:
    tool_list = (
        "Allowed tools: create_workbook, open_workbook, load_portfolio, add_section, "
        "add_chart, render_report, show_state."
    )
    steps = (
        "Step order: 1) create_workbook or open_workbook, "
        "2) load_portfolio (required if portfolio missing), "
        "3) add_section with section_type=asset_allocation, "
        "4) add_chart (chart_type=pie, data_source=portfolio), "
        "5) render_report."
    )
    clarifier = (
        "Clarifying question rule: if portfolio data is missing, ask exactly one "
        "question to request a minimal portfolio JSON before proceeding."
    )
    content = (
        f"You are a report portal agent creating '{report_title}'. {tool_list} {steps} "
        f"{clarifier}"
    )
    return {"messages": [{"role": "system", "content": content}]}


@mcp.prompt()
def generic_report_skill(report_title: str = "Report") -> Dict[str, Any]:
    content = (
        f"You are a report portal agent creating '{report_title}'. "
        "Use the provided tools to build and render the report."
    )
    return {"messages": [{"role": "system", "content": content}]}


if __name__ == "__main__":
    mcp.run(transport="stdio")
