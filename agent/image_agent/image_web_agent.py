from langgraph.graph import StateGraph, START, END
from langchain_core.runnables import RunnableConfig
from typing_extensions import Annotated, TypedDict
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.runtime import Runtime
from IPython.display import Image, display
from langgraph.prebuilt import ToolNode, tools_condition
import yaml

data = yaml.safe_load(open("data/config.yaml"))

class GraphStateData(TypedDict):
    client_name: str

graph = StateGraph(state_schema=GraphStateData)


class ImageWebAgent(client_name: str):

    def __init__(self, self.client_name: str) -> None:
        self.client_name = client_name


    def input_text(self):
        return

    def scraper_api_search(self, query: str) -> str:
        return "Scraper API search result for query: " + query

    def response(self, prompt: str, max_length: int = 50) -> str:
        graph.add_edge(START, "image_agent")
        graph.add_node("image_agent", input_text)
        graph.set_entry_point("image_agent")
        graph.add_node("tool_web_1", ToolNode(tool_name="scraper_api_search"))
        graph.add_node("tool_web_2", ToolNode(tool_name="scrappey_search"))
        graph.add_node("tool_web_3", ToolNode(tool_name="google_scrapper_search"))
        graph.add_node("tool_web_4", ToolNode(tool_name="outscrapper_search"))
        graph.add_conditional_edge("image_agent", "tool_web_1", condition=tools_condition)
        graph.add_conditional_edge("image_agent", "tool_web_2", condition=tools_condition)
        graph.add_conditional_edge("image_agent", "tool_web_3", condition=tools_condition)
        graph.add_conditional_edge("image_agent", "tool_web_4", condition=tools_condition)
        graph.add_edge("tool_web_1", "image_agent")
        graph.add_edge("tool_web_2", "image_agent")
        graph.add_edge("tool_web_3", "image_agent")
        graph.add_edge("tool_web_4", "image_agent")
        executer = graph.compile()
        result = executer.invoke({"logo": self.logo})
        path_image = result.get()
        return generated_text