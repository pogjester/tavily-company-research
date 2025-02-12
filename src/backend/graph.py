from langchain_core.messages import SystemMessage, AIMessage
from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver

# Import research state class
from .classes.state import ResearchState, InputState, OutputState

# Import node classes
from .nodes import GroundingNode

class Graph:
    def __init__(self, company=None, url=None, hq_location=None, industry=None):
        # Initial setup of ResearchState and messages
        self.messages = [
            SystemMessage(content="You are an expert researcher ready to begin the information gathering process.")
        ]

        #Initialize InputState
        self.input_state = InputState(
            company=company,
            company_url=url,
            hq_location=hq_location,
            industry=industry
        )

        # Initialize nodes as attributes
        self.ground = GroundingNode()

        # Initialize workflow for the graph
        self.workflow = StateGraph(ResearchState, input=InputState, output=OutputState)

        # Add nodes to the workflow
        self.workflow.add_node("grounding", self.ground.run)

        # Set start node
        self.workflow.set_entry_point("grounding")

        # Add memory saver to the workflow
        self.memory = MemorySaver()

    async def run(self, progress_callback=None):
        # Compile the graph
        graph = self.workflow.compile(checkpointer=self.memory)
        thread = {"configurable": {"thread_id": "2"}}

        # Execute the graph asynchronously and send progress updates
        async for s in graph.astream(self.input_state, thread, stream_mode="values"):
            if "messages" in s and s["messages"]:  # Check if "messages" exists and is non-empty
                message = s["messages"][-1]
                output_message = message.content if hasattr(message, "content") else str(message)
                if progress_callback and not getattr(message, "is_manual_selection", False):
                    await progress_callback(output_message)

    def compile(self):
        # Use a consistent thread ID for state persistence
        thread = {"configurable": {"thread_id": "2"}}

        # Compile the workflow with checkpointer and interrupt configuration
        graph = self.workflow.compile(
            checkpointer=self.memory
        )
        return graph
        
        