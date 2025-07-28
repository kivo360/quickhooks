"""Tests for agent analysis functionality."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path

from quickhooks.agent_analysis import (
    AgentAnalyzer,
    AgentAnalysisRequest,
    AgentAnalysisResponse,
    AgentRecommendation,
    AgentCapability,
    ContextChunk,
    ContextManager,
    DiscoveredAgentInfo
)
from quickhooks.agent_analysis.agent_discovery import AgentDiscovery, DiscoveredAgent


class TestContextManager:
    """Test the context management functionality."""
    
    def test_estimate_tokens_regular_text(self):
        """Test token estimation for regular text."""
        cm = ContextManager()
        text = "This is a simple sentence with some words."
        tokens = cm.estimate_tokens(text)
        # Should be roughly len(text) / 4.2
        expected = int(len(text) / 4.2)
        assert abs(tokens - expected) <= 2  # Allow small variance
    
    def test_estimate_tokens_code_heavy(self):
        """Test token estimation for code-heavy content."""
        cm = ContextManager()
        code_text = """
        def test_function():
            import os
            class TestClass:
                def __init__(self):
                    self.value = {}
            for i in range(10):
                if i > 5:
                    console.log("test")
        """
        tokens = cm.estimate_tokens(code_text)
        # Should be roughly len(text) / 3.5 for code
        expected = int(len(code_text) / 3.5)
        assert abs(tokens - expected) <= 5  # Allow variance
    
    def test_estimate_tokens_technical_text(self):
        """Test token estimation for technical text."""
        cm = ContextManager()
        tech_text = "This API uses HTTP endpoints with JSON authentication to access the database server."
        tokens = cm.estimate_tokens(tech_text)
        # Should be roughly len(text) / 3.8 for technical content
        expected = int(len(tech_text) / 3.8)
        assert abs(tokens - expected) <= 2
    
    def test_chunk_context_fits_within_limit(self):
        """Test context chunking when content fits within limits."""
        cm = ContextManager(max_tokens=1000)
        context = "Short context that fits easily."
        prompt = "Test prompt"
        
        chunks = cm.chunk_context(context, prompt)
        
        assert len(chunks) == 1
        assert chunks[0].chunk_type == "complete"
        assert chunks[0].content == context
    
    def test_chunk_context_requires_chunking(self):
        """Test context chunking when content exceeds limits."""
        cm = ContextManager(max_tokens=100)  # Very small limit
        
        # Create large context
        context = "This is a very long context. " * 50  # Should exceed limit
        prompt = "Test prompt"
        
        chunks = cm.chunk_context(context, prompt)
        
        # Should have start and end chunks
        assert len(chunks) == 2
        chunk_types = [chunk.chunk_type for chunk in chunks]
        assert "start" in chunk_types
        assert "end" in chunk_types
    
    def test_chunk_context_empty_context(self):
        """Test context chunking with empty context."""
        cm = ContextManager()
        chunks = cm.chunk_context("", "Test prompt")
        assert len(chunks) == 0
    
    def test_calculate_total_tokens(self):
        """Test total token calculation."""
        cm = ContextManager()
        chunks = [
            ContextChunk(content="chunk1", chunk_type="start", token_count=10, position=0),
            ContextChunk(content="chunk2", chunk_type="end", token_count=15, position=100)
        ]
        prompt = "Test prompt"
        
        total = cm.calculate_total_tokens(chunks, prompt)
        expected = 10 + 15 + cm.estimate_tokens(prompt)
        assert total == expected


class TestAgentAnalysisTypes:
    """Test the type definitions."""
    
    def test_agent_recommendation_creation(self):
        """Test creating an AgentRecommendation."""
        rec = AgentRecommendation(
            agent_type=AgentCapability.CODING,
            confidence=0.85,
            reasoning="Good fit for coding task",
            threshold_met=True,
            priority=1
        )
        
        assert rec.agent_type == AgentCapability.CODING
        assert rec.confidence == 0.85
        assert rec.threshold_met is True
        assert rec.priority == 1
    
    def test_agent_analysis_request_validation(self):
        """Test AgentAnalysisRequest validation."""
        request = AgentAnalysisRequest(
            prompt="Test prompt",
            context="Additional context",
            max_context_tokens=100000,
            confidence_threshold=0.8
        )
        
        assert request.prompt == "Test prompt"
        assert request.context == "Additional context"
        assert request.max_context_tokens == 100000
        assert request.confidence_threshold == 0.8
    
    def test_agent_analysis_request_defaults(self):
        """Test AgentAnalysisRequest with default values."""
        request = AgentAnalysisRequest(prompt="Test prompt")
        
        assert request.context is None
        assert request.max_context_tokens == 128000
        assert request.confidence_threshold == 0.7
    
    def test_agent_analysis_response_properties(self):
        """Test AgentAnalysisResponse computed properties."""
        recommendations = [
            AgentRecommendation(
                agent_type=AgentCapability.CODING,
                confidence=0.9,
                reasoning="High confidence",
                threshold_met=True,
                priority=2
            ),
            AgentRecommendation(
                agent_type=AgentCapability.TESTING,
                confidence=0.8,
                reasoning="Good fit",
                threshold_met=True,
                priority=1
            ),
            AgentRecommendation(
                agent_type=AgentCapability.ANALYSIS,
                confidence=0.6,
                reasoning="Low confidence",
                threshold_met=False,
                priority=3
            )
        ]
        
        response = AgentAnalysisResponse(
            recommendations=recommendations,
            context_used=[],
            total_tokens_used=1000,
            analysis_summary="Test analysis",
            multiple_agents_recommended=True
        )
        
        # Test top_recommendation (should be priority 1)
        top = response.top_recommendation
        assert top is not None
        assert top.agent_type == AgentCapability.TESTING
        assert top.priority == 1
        
        # Test qualified_recommendations (should exclude threshold_met=False)
        qualified = response.qualified_recommendations
        assert len(qualified) == 2
        assert all(rec.threshold_met for rec in qualified)


class TestAgentAnalyzer:
    """Test the AgentAnalyzer class."""
    
    @pytest.fixture
    def mock_groq_response(self):
        """Mock response from Groq model."""
        return AgentAnalysisResponse(
            recommendations=[
                AgentRecommendation(
                    agent_type=AgentCapability.CODING,
                    confidence=0.9,
                    reasoning="This appears to be a coding task",
                    threshold_met=True,
                    priority=1
                )
            ],
            context_used=[],
            total_tokens_used=500,
            analysis_summary="Analysis suggests coding agent is most appropriate",
            multiple_agents_recommended=False
        )
    
    def test_init_with_api_key(self):
        """Test AgentAnalyzer initialization with API key."""
        analyzer = AgentAnalyzer(groq_api_key="test-key")
        assert analyzer.model is not None
        assert analyzer.context_manager is not None
        assert analyzer.agent is not None
    
    def test_init_without_api_key_raises_error(self):
        """Test that missing API key raises ValueError."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="GROQ_API_KEY"):
                AgentAnalyzer()
    
    @patch.dict('os.environ', {'GROQ_API_KEY': 'test-key'})
    def test_init_with_env_var(self):
        """Test initialization with environment variable."""
        analyzer = AgentAnalyzer()
        assert analyzer.model is not None
    
    def test_available_capabilities(self):
        """Test getting available capabilities."""
        analyzer = AgentAnalyzer(groq_api_key="test-key")
        capabilities = analyzer.available_capabilities
        
        assert isinstance(capabilities, list)
        assert len(capabilities) > 0
        assert "coding" in capabilities
        assert "analysis" in capabilities
    
    @patch.dict('os.environ', {'GROQ_API_KEY': 'test-key'})
    @patch('quickhooks.agent_analysis.analyzer.Agent')
    def test_analyze_prompt_sync(self, mock_agent_class, mock_groq_response):
        """Test synchronous prompt analysis."""
        # Setup mock
        mock_agent_instance = Mock()
        mock_agent_instance.run_sync.return_value = Mock(output=mock_groq_response)
        mock_agent_class.return_value = mock_agent_instance
        
        analyzer = AgentAnalyzer()
        request = AgentAnalysisRequest(prompt="Write a Python function")
        
        result = analyzer.analyze_prompt_sync(request)
        
        assert isinstance(result, AgentAnalysisResponse)
        assert len(result.recommendations) > 0
        mock_agent_instance.run_sync.assert_called_once()
    
    @patch.dict('os.environ', {'GROQ_API_KEY': 'test-key'})
    @patch('quickhooks.agent_analysis.analyzer.Agent')
    @pytest.mark.asyncio
    async def test_analyze_prompt_async(self, mock_agent_class, mock_groq_response):
        """Test asynchronous prompt analysis."""
        # Setup mock
        mock_agent_instance = Mock()
        mock_agent_instance.run = AsyncMock(return_value=Mock(output=mock_groq_response))
        mock_agent_class.return_value = mock_agent_instance
        
        analyzer = AgentAnalyzer()
        request = AgentAnalysisRequest(prompt="Write a Python function")
        
        result = await analyzer.analyze_prompt(request)
        
        assert isinstance(result, AgentAnalysisResponse)
        assert len(result.recommendations) > 0
        mock_agent_instance.run.assert_called_once()
    
    def test_build_analysis_prompt_with_context(self):
        """Test building analysis prompt with context chunks."""
        analyzer = AgentAnalyzer(groq_api_key="test-key")
        request = AgentAnalysisRequest(
            prompt="Test prompt",
            confidence_threshold=0.8
        )
        context_chunks = [
            ContextChunk(
                content="Context content",
                chunk_type="complete",
                token_count=50,
                position=0
            )
        ]
        
        prompt = analyzer._build_analysis_prompt(request, context_chunks)
        
        assert "Test prompt" in prompt
        assert "Context content" in prompt
        assert "0.8" in prompt
        assert "ANALYZE THIS PROMPT" in prompt
    
    def test_build_analysis_prompt_without_context(self):
        """Test building analysis prompt without context."""
        analyzer = AgentAnalyzer(groq_api_key="test-key")
        request = AgentAnalysisRequest(prompt="Test prompt")
        context_chunks = []
        
        prompt = analyzer._build_analysis_prompt(request, context_chunks)
        
        assert "Test prompt" in prompt
        assert "CONTEXT INFORMATION" not in prompt
        assert "ANALYZE THIS PROMPT" in prompt


@pytest.mark.integration
class TestAgentAnalysisIntegration:
    """Integration tests requiring actual API calls (when API key is available)."""
    
    @pytest.mark.skipif(
        not pytest.importorskip("os").getenv("GROQ_API_KEY"),
        reason="GROQ_API_KEY not set"
    )
    def test_real_analysis_simple_coding_task(self):
        """Test real analysis with a simple coding task."""
        analyzer = AgentAnalyzer()
        request = AgentAnalysisRequest(
            prompt="Write a Python function that calculates the factorial of a number",
            confidence_threshold=0.6
        )
        
        result = analyzer.analyze_prompt_sync(request)
        
        assert isinstance(result, AgentAnalysisResponse)
        assert len(result.recommendations) > 0
        assert result.analysis_summary
        
        # Should recommend coding agent for this task
        coding_recs = [r for r in result.recommendations if r.agent_type == AgentCapability.CODING]
        assert len(coding_recs) > 0
        assert any(rec.threshold_met for rec in coding_recs)
    
    @pytest.mark.skipif(
        not pytest.importorskip("os").getenv("GROQ_API_KEY"),
        reason="GROQ_API_KEY not set"
    )
    def test_real_analysis_with_context(self):
        """Test real analysis with context."""
        analyzer = AgentAnalyzer()
        context = """
        This is a Python project using FastAPI for web development.
        The codebase includes user authentication, database models,
        and API endpoints for a todo application.
        """
        
        request = AgentAnalysisRequest(
            prompt="Review the authentication code for security issues",
            context=context,
            confidence_threshold=0.5
        )
        
        result = analyzer.analyze_prompt_sync(request)
        
        assert isinstance(result, AgentAnalysisResponse)
        assert len(result.recommendations) > 0
        assert result.total_tokens_used > 0
        
        # Should recommend code review or analysis agent
        relevant_types = [AgentCapability.CODE_REVIEW, AgentCapability.ANALYSIS, AgentCapability.DEBUGGING]
        relevant_recs = [r for r in result.recommendations if r.agent_type in relevant_types]
        assert len(relevant_recs) > 0


class TestAgentDiscovery:
    """Test the agent discovery functionality."""
    
    @pytest.fixture
    def temp_agents_dir(self, tmp_path):
        """Create a temporary agents directory with test agents."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        
        # Create a Python agent
        python_agent = agents_dir / "test_coder.py"
        python_agent.write_text('''"""
A coding assistant that helps with Python development tasks.
Capabilities: coding, testing, debugging
Usage: Use for Python programming tasks
"""

class CodingAgent:
    def help_with_coding(self):
        pass
''')
        
        # Create a Markdown agent
        md_agent = agents_dir / "doc_writer.md"
        md_agent.write_text('''# Documentation Writer

A specialized agent for writing technical documentation.

## Capabilities
- documentation
- writing
- explaining

## Usage
Use this agent when you need to create or improve documentation.
''')
        
        # Create a JSON agent
        json_agent = agents_dir / "data_analyzer.json"
        json_agent.write_text('''{
    "description": "Analyzes data and provides insights",
    "capabilities": ["analysis", "data", "research"],
    "usage": "Use for data analysis and research tasks"
}''')
        
        return agents_dir
    
    @pytest.fixture
    def temp_db_path(self, tmp_path):
        """Create a temporary database path."""
        return tmp_path / "test_db"
    
    def test_agent_discovery_init(self, temp_agents_dir, temp_db_path):
        """Test AgentDiscovery initialization."""
        discovery = AgentDiscovery(agents_dir=temp_agents_dir, db_path=temp_db_path)
        
        assert discovery.agents_dir == temp_agents_dir
        assert discovery.db_path == temp_db_path
        assert discovery.encoder is not None
        assert discovery.client is not None
        assert discovery.collection is not None
    
    def test_scan_and_index_agents(self, temp_agents_dir, temp_db_path):
        """Test scanning and indexing agents."""
        discovery = AgentDiscovery(agents_dir=temp_agents_dir, db_path=temp_db_path)
        
        count = discovery.scan_and_index_agents()
        
        assert count == 3  # Should find 3 test agents
        
        # Test that agents are indexed
        stats = discovery.get_collection_stats()
        assert stats["total_agents"] == 3
    
    def test_find_relevant_agents(self, temp_agents_dir, temp_db_path):
        """Test finding relevant agents."""
        discovery = AgentDiscovery(agents_dir=temp_agents_dir, db_path=temp_db_path)
        discovery.scan_and_index_agents()
        
        # Search for coding-related prompt
        relevant = discovery.find_relevant_agents(
            prompt="Help me write a Python function",
            limit=2,
            min_similarity=0.1  # Low threshold for testing
        )
        
        assert len(relevant) > 0
        assert all(isinstance(agent, DiscoveredAgent) for agent in relevant)
        assert all(agent.similarity_score >= 0.1 for agent in relevant)
    
    def test_parse_python_agent(self, temp_agents_dir, temp_db_path):
        """Test parsing Python agent files."""
        discovery = AgentDiscovery(agents_dir=temp_agents_dir, db_path=temp_db_path)
        
        python_file = temp_agents_dir / "test_coder.py"
        agent = discovery._parse_agent_file(python_file)
        
        assert agent is not None
        assert agent.name == "test_coder"
        assert "coding" in [cap.lower() for cap in agent.capabilities]
        assert len(agent.description) > 0
    
    def test_parse_markdown_agent(self, temp_agents_dir, temp_db_path):
        """Test parsing Markdown agent files."""
        discovery = AgentDiscovery(agents_dir=temp_agents_dir, db_path=temp_db_path)
        
        md_file = temp_agents_dir / "doc_writer.md"
        agent = discovery._parse_agent_file(md_file)
        
        assert agent is not None
        assert agent.name == "doc_writer"
        assert "documentation" in agent.capabilities
        assert "Documentation Writer" in agent.description
    
    def test_parse_json_agent(self, temp_agents_dir, temp_db_path):
        """Test parsing JSON agent files."""
        discovery = AgentDiscovery(agents_dir=temp_agents_dir, db_path=temp_db_path)
        
        json_file = temp_agents_dir / "data_analyzer.json"
        agent = discovery._parse_agent_file(json_file)
        
        assert agent is not None
        assert agent.name == "data_analyzer"
        assert "analysis" in agent.capabilities
        assert "data analysis" in agent.description.lower()
    
    def test_force_reindex(self, temp_agents_dir, temp_db_path):
        """Test force reindexing of agents."""
        discovery = AgentDiscovery(agents_dir=temp_agents_dir, db_path=temp_db_path)
        
        # Index once
        count1 = discovery.scan_and_index_agents()
        assert count1 == 3
        
        # Index again without force (should be 0 new)
        count2 = discovery.scan_and_index_agents(force_reindex=False)
        assert count2 == 0
        
        # Force reindex (should be 3 again)
        count3 = discovery.scan_and_index_agents(force_reindex=True)
        assert count3 == 3


class TestDiscoveredAgentInfo:
    """Test the DiscoveredAgentInfo type."""
    
    def test_discovered_agent_info_creation(self):
        """Test creating a DiscoveredAgentInfo."""
        agent_info = DiscoveredAgentInfo(
            name="test_agent",
            path="/path/to/agent.py",
            description="A test agent",
            capabilities=["coding", "testing"],
            similarity_score=0.85,
            usage_pattern="Use for testing"
        )
        
        assert agent_info.name == "test_agent"
        assert agent_info.path == "/path/to/agent.py"
        assert agent_info.similarity_score == 0.85
        assert "coding" in agent_info.capabilities


class TestIntegratedAgentAnalysis:
    """Test the integrated agent analysis with discovery."""
    
    @pytest.fixture
    def mock_analyzer_with_discovery(self, temp_agents_dir, temp_db_path):
        """Create a mock analyzer with agent discovery."""
        with patch.dict('os.environ', {'GROQ_API_KEY': 'test-key'}):
            analyzer = AgentAnalyzer(enable_agent_discovery=True)
            # Replace with test paths
            analyzer.agent_discovery.agents_dir = temp_agents_dir
            analyzer.agent_discovery.db_path = temp_db_path
            return analyzer
    
    def test_analyzer_with_discovery_enabled(self, temp_agents_dir, temp_db_path):
        """Test analyzer initialization with discovery enabled."""
        with patch.dict('os.environ', {'GROQ_API_KEY': 'test-key'}):
            analyzer = AgentAnalyzer(enable_agent_discovery=True)
            assert analyzer.agent_discovery is not None
    
    def test_analyzer_with_discovery_disabled(self):
        """Test analyzer initialization with discovery disabled."""
        with patch.dict('os.environ', {'GROQ_API_KEY': 'test-key'}):
            analyzer = AgentAnalyzer(enable_agent_discovery=False)
            assert analyzer.agent_discovery is None
    
    @patch('quickhooks.agent_analysis.analyzer.Agent')
    def test_analyze_with_discovered_agents(self, mock_agent_class, mock_analyzer_with_discovery, temp_agents_dir):
        """Test analysis with discovered agents."""
        # Setup mock response
        mock_response = AgentAnalysisResponse(
            recommendations=[
                AgentRecommendation(
                    agent_type=AgentCapability.CODING,
                    confidence=0.9,
                    reasoning="Good for coding",
                    threshold_met=True,
                    priority=1
                )
            ],
            discovered_agents=[],
            context_used=[],
            total_tokens_used=500,
            analysis_summary="Test analysis",
            multiple_agents_recommended=False,
            claude_code_prompt_modification="Use the test_coder agent to write Python code."
        )
        
        mock_agent_instance = Mock()
        mock_agent_instance.run_sync.return_value = Mock(output=mock_response)
        mock_agent_class.return_value = mock_agent_instance
        
        # Create test agents
        python_agent = temp_agents_dir / "test_coder.py"
        python_agent.write_text('"""A Python coding agent."""\nclass CodingAgent: pass')
        
        request = AgentAnalysisRequest(prompt="Write a Python function")
        result = mock_analyzer_with_discovery.analyze_prompt_sync(request)
        
        assert isinstance(result, AgentAnalysisResponse)
        assert result.claude_code_prompt_modification is not None
        mock_agent_instance.run_sync.assert_called_once()
    
    def test_build_analysis_prompt_with_discovered_agents(self, mock_analyzer_with_discovery):
        """Test building analysis prompt with discovered agents."""
        request = AgentAnalysisRequest(prompt="Test prompt")
        context_chunks = []
        discovered_agents = [
            DiscoveredAgentInfo(
                name="test_agent",
                path="/path/to/agent.py",
                description="A test agent",
                capabilities=["coding"],
                similarity_score=0.8,
                usage_pattern="Use for coding tasks"
            )
        ]
        
        prompt = mock_analyzer_with_discovery._build_analysis_prompt(
            request, context_chunks, discovered_agents
        )
        
        assert "DISCOVERED LOCAL AGENTS" in prompt
        assert "test_agent" in prompt
        assert "A test agent" in prompt
        assert "coding" in prompt
        assert "0.80" in prompt  # similarity score


class TestAgentAnalysisWithModifiedPrompt:
    """Test the modified prompt generation functionality."""
    
    def test_response_with_claude_code_modification(self):
        """Test response includes Claude Code prompt modification."""
        response = AgentAnalysisResponse(
            recommendations=[],
            discovered_agents=[],
            context_used=[],
            total_tokens_used=100,
            analysis_summary="Test",
            multiple_agents_recommended=False,
            claude_code_prompt_modification="Use the coding_expert agent to write Python code for data analysis."
        )
        
        assert response.claude_code_prompt_modification is not None
        assert "coding_expert" in response.claude_code_prompt_modification
        assert "agent" in response.claude_code_prompt_modification.lower()
    
    def test_response_properties_with_discovered_agents(self):
        """Test response properties work with discovered agents."""
        discovered_agents = [
            DiscoveredAgentInfo(
                name="local_agent",
                path="/path/to/local.py",
                description="A local agent",
                capabilities=["coding"],
                similarity_score=0.9,
                usage_pattern="Use for local tasks"
            )
        ]
        
        response = AgentAnalysisResponse(
            recommendations=[],
            discovered_agents=discovered_agents,
            context_used=[],
            total_tokens_used=100,
            analysis_summary="Found local agents",
            multiple_agents_recommended=False
        )
        
        assert len(response.discovered_agents) == 1
        assert response.discovered_agents[0].name == "local_agent"
        assert response.discovered_agents[0].similarity_score == 0.9