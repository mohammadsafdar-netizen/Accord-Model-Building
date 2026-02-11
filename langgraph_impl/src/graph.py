from langgraph.graph import StateGraph, END
from src.state import UniversalState
from src.nodes import (
    orchestrator_node,
    input_validator_node,
    schema_mapper_node,
    conversation_manager_node,
    form_population_node,
    completeness_verification_node,
    email_processing_node,
    document_intelligence_node,
    guidewire_integration_node,
    user_preference_node
)

def define_graph():
    # 1. Initialize Graph
    workflow = StateGraph(UniversalState)

    # 2. Add Nodes
    workflow.add_node("orchestrator", orchestrator_node)
    
    workflow.add_node("input_validator", input_validator_node)
    workflow.add_node("schema_mapper", schema_mapper_node)
    workflow.add_node("conversation_manager", conversation_manager_node)
    workflow.add_node("form_population", form_population_node)
    workflow.add_node("completeness_verification", completeness_verification_node)
    workflow.add_node("email_processing", email_processing_node)
    workflow.add_node("document_intelligence", document_intelligence_node)
    workflow.add_node("guidewire_integration", guidewire_integration_node)
    workflow.add_node("user_preference", user_preference_node)

    # 3. Define Edges
    
    # Entry Point
    workflow.set_entry_point("orchestrator")
    
    # Conditional Logic for Orchestrator
    def router(state: UniversalState):
        next_agent = state.get("next_agent")
        
        # Mapping generic names to specific node names
        mapping = {
            "input_validator": "input_validator",
            "schema_mapper": "schema_mapper",
            "conversation_manager": "conversation_manager",
            "form_population": "form_population",
            "completeness_verification": "completeness_verification",
            "email_processing": "email_processing",
            "document_intelligence": "document_intelligence",
            "guidewire_integration": "guidewire_integration",
            "user_preference": "user_preference"
        }
        
        return mapping.get(next_agent, END)

    workflow.add_conditional_edges(
        "orchestrator",
        router
    )
    
    # All agents return to Orchestrator to decide next step
    # (Or they could modify state and let next iteration handle it)
    workflow.add_edge("input_validator", "orchestrator")
    workflow.add_edge("schema_mapper", "orchestrator")
    workflow.add_edge("conversation_manager", "orchestrator")
    workflow.add_edge("form_population", "orchestrator")
    workflow.add_edge("completeness_verification", "orchestrator")
    workflow.add_edge("email_processing", "orchestrator")
    workflow.add_edge("document_intelligence", "orchestrator")
    workflow.add_edge("guidewire_integration", "orchestrator")
    workflow.add_edge("user_preference", "orchestrator")

    return workflow.compile()
