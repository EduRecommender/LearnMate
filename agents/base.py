from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class AgentResponse:
    """Standard response format for all agents"""
    success: bool
    data: Any
    error: Optional[str] = None
    metadata: Optional[Dict] = None

@dataclass
class AgentContext:
    """Context information passed between agents"""
    session_id: str
    user_id: str
    timestamp: datetime
    preferences: Dict[str, Any]
    study_goals: Dict[str, Any]
    current_state: Dict[str, Any]

class BaseAgent(ABC):
    """Base class for all agents in the system"""
    
    def __init__(self, agent_id: str, agent_type: str):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.context: Optional[AgentContext] = None
    
    def set_context(self, context: AgentContext) -> None:
        """Set the current context for the agent"""
        self.context = context
    
    @abstractmethod
    async def process(self, input_data: Dict[str, Any]) -> AgentResponse:
        """Process the input data and return a response"""
        pass
    
    @abstractmethod
    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate the input data"""
        pass
    
    def _create_error_response(self, error_message: str) -> AgentResponse:
        """Create an error response"""
        return AgentResponse(
            success=False,
            data=None,
            error=error_message
        )
    
    def _create_success_response(self, data: Any, metadata: Optional[Dict] = None) -> AgentResponse:
        """Create a success response"""
        return AgentResponse(
            success=True,
            data=data,
            metadata=metadata
        )
    
    async def handle_error(self, error: Exception) -> AgentResponse:
        """Handle errors in a standardized way"""
        return self._create_error_response(str(error))

class ContentAgent(BaseAgent):
    """Base class for content retrieval agents"""
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id, "content")
    
    @abstractmethod
    async def search_content(self, query: Dict[str, Any]) -> AgentResponse:
        """Search for relevant content"""
        pass
    
    @abstractmethod
    async def validate_content(self, content: Dict[str, Any]) -> bool:
        """Validate retrieved content"""
        pass

class StrategyAgent(BaseAgent):
    """Base class for study strategy agents"""
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id, "strategy")
    
    @abstractmethod
    async def recommend_strategy(self, content: Dict[str, Any]) -> AgentResponse:
        """Recommend a study strategy for the given content"""
        pass
    
    @abstractmethod
    async def validate_strategy(self, strategy: Dict[str, Any]) -> bool:
        """Validate the recommended strategy"""
        pass

class MetaAgent(BaseAgent):
    """Base class for the meta-agent that orchestrates other agents"""
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id, "meta")
        self.agents: Dict[str, BaseAgent] = {}
    
    def register_agent(self, agent: BaseAgent) -> None:
        """Register a new agent"""
        self.agents[agent.agent_id] = agent
    
    @abstractmethod
    async def orchestrate(self, task: Dict[str, Any]) -> AgentResponse:
        """Orchestrate the execution of multiple agents"""
        pass
    
    @abstractmethod
    async def validate_plan(self, plan: Dict[str, Any]) -> bool:
        """Validate the generated study plan"""
        pass

class AssistantAgent(BaseAgent):
    """Base class for the conversational assistant agent"""
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id, "assistant")
    
    @abstractmethod
    async def process_message(self, message: str) -> AgentResponse:
        """Process a user message"""
        pass
    
    @abstractmethod
    async def generate_response(self, context: Dict[str, Any]) -> str:
        """Generate a response based on context"""
        pass 