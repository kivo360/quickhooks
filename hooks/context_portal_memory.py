#!/usr/bin/env python3
"""
QuickHook: Enhanced Context Portal Memory Management with Dual-AI Decision Making

Integrates Context Portal MCP with dual-AI analysis for intelligent project memory management.
Features background processing and advanced decision-making capabilities using Pydantic AI.
"""

import asyncio
import hashlib
import json
import os
import sqlite3
import sys
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.groq import GroqModel
from pydantic_ai.providers.groq import GroqProvider


# Enhanced Pydantic schemas for decision analysis
class ConceptExtraction(BaseModel):
    """Extracted concepts from tool usage"""
    concepts: list[str] = Field(default_factory=list, description="Key concepts identified")
    importance_score: float = Field(0.0, ge=0.0, le=1.0, description="Importance of concepts")
    categories: list[str] = Field(default_factory=list, description="Concept categories")
    relationships: dict[str, list[str]] = Field(default_factory=dict, description="Concept relationships")


class DecisionAnalysis(BaseModel):
    """Analysis of decisions being made"""
    decision_type: str = Field("unknown", description="Type of decision (architectural, implementation, etc.)")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Confidence in decision analysis")
    impact_areas: list[str] = Field(default_factory=list, description="Areas likely to be impacted")
    recommended_storage: bool = Field(False, description="Whether this should be stored long-term")
    priority: str = Field("medium", description="Priority level (low, medium, high)")


class ContextualMemory(BaseModel):
    """Contextual memory analysis"""
    should_remember: bool = Field(False, description="Whether this context should be remembered")
    memory_type: str = Field("temporary", description="Type of memory (temporary, session, persistent)")
    recall_triggers: list[str] = Field(default_factory=list, description="What should trigger recall of this memory")
    relevance_score: float = Field(0.0, ge=0.0, le=1.0, description="Relevance for future sessions")


class EnhancedContextPortalMemoryManager:
    """Enhanced memory manager with AI-powered decision making."""

    def __init__(self, project_root: str | None = None):
        """Initialize the enhanced Context Portal memory manager."""
        self.project_root = project_root or os.getcwd()
        self.db_path = Path(self.project_root) / ".context-portal" / "project.db"
        self.db_path.parent.mkdir(exist_ok=True)
        self._init_database()
        self._init_ai_agents()
        self._init_mcp_client()
        
        # Background processing queue
        self._background_queue = asyncio.Queue()
        self._background_task = None
        self._loop = None

    def _init_ai_agents(self):
        """Initialize AI agents for decision making."""
        groq_api_key = os.getenv("GROQ_API_KEY")
        if not groq_api_key:
            print("Warning: GROQ_API_KEY not set, AI analysis disabled", file=sys.stderr)
            self.ai_enabled = False
            return
        
        self.ai_enabled = True
        
        try:
            # Concept extraction agent (qwen3-32b)
            self.concept_agent = Agent(
                GroqModel('qwen/qwen3-32b', provider=GroqProvider(api_key=groq_api_key)),
                output_type=ConceptExtraction,
                system_prompt="""You are an expert at extracting key concepts from developer tool usage.
                
Analyze the tool usage and extract:
1. Key concepts being introduced or worked with
2. Importance score based on context and complexity
3. Categories (technical, business, architectural, etc.)
4. Relationships between concepts

Focus on concepts that should be remembered for future development sessions."""
            )
            
            # Decision analysis agent with reasoning (kimi-k2-instruct)  
            self.decision_agent = Agent(
                GroqModel('moonshotai/kimi-k2-instruct', provider=GroqProvider(api_key=groq_api_key)),
                output_type=DecisionAnalysis,
                system_prompt="""You are an expert at analyzing development decisions from tool usage patterns with deep reasoning capabilities.

Use your reasoning to analyze the tool usage and identify:
1. What type of decision is being made (think through the context and patterns)
2. Confidence in the decision analysis (reason about the evidence quality)
3. Areas that will be impacted (consider ripple effects and dependencies)
4. Whether this decision should be stored long-term (evaluate importance and reusability)
5. Priority level for this decision (weigh urgency vs impact)

Think step by step about architectural decisions, implementation choices, debugging strategies, and design patterns.
Use the MCP client capabilities to access relevant context when needed.""",
                toolsets=[]  # Will be populated with MCP client when available
            )
            
            # Contextual memory agent (qwen3-32b)
            self.memory_agent = Agent(
                GroqModel('qwen/qwen3-32b', provider=GroqProvider(api_key=groq_api_key)),
                output_type=ContextualMemory,
                system_prompt="""You are an expert at determining what information should be remembered across development sessions.
                
Analyze the context and determine:
1. Whether this should be remembered beyond the current session
2. What type of memory this is (temporary, session-scoped, persistent)
3. What future events should trigger recall of this information
4. Relevance score for future development work

Consider patterns, configurations, important file locations, architectural decisions, and debugging insights."""
            )
            
        except Exception as e:
            print(f"Warning: Failed to initialize AI agents: {e}", file=sys.stderr)
            self.ai_enabled = False

    def _init_mcp_client(self):
        """Initialize MCP client for Context Portal integration."""
        try:
            from pydantic_ai.mcp import MCPServerStdio
            
            # Try to initialize Context Portal MCP server for the decision agent using proper uvx command
            self.mcp_server = MCPServerStdio(
                command='uvx',
                args=[
                    '--from',
                    'context-portal-mcp',
                    'conport-mcp',
                    '--mode',
                    'stdio',
                    '--workspace_id',
                    self.project_root,
                    '--log-file',
                    './logs/conport.log',
                    '--log-level',
                    'INFO'
                ],
                allow_sampling=True,
                tool_prefix='conport'
            )
            
            # Add MCP server to decision agent's toolsets if AI is enabled
            if self.ai_enabled and hasattr(self, 'decision_agent'):
                self.decision_agent._toolsets = [self.mcp_server]
                print("Context Portal MCP client initialized for Kimi-K2 decision agent", file=sys.stderr)
                
        except Exception as e:
            print(f"Warning: Failed to initialize MCP client: {e}", file=sys.stderr)
            self.mcp_server = None

    def _init_database(self):
        """Initialize the enhanced Context Portal database schema."""
        with sqlite3.connect(self.db_path) as conn:
            # First, add missing columns to existing tables if they don't exist
            try:
                conn.execute("ALTER TABLE decisions ADD COLUMN decision_type TEXT")
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            try:
                conn.execute("ALTER TABLE decisions ADD COLUMN impact_areas TEXT")
            except sqlite3.OperationalError:
                pass
                
            try:
                conn.execute("ALTER TABLE decisions ADD COLUMN confidence REAL DEFAULT 0.0")
            except sqlite3.OperationalError:
                pass
                
            try:
                conn.execute("ALTER TABLE decisions ADD COLUMN ai_analysis TEXT")
            except sqlite3.OperationalError:
                pass
            
            # Add missing columns to context_entries if they don't exist
            try:
                conn.execute("ALTER TABLE context_entries ADD COLUMN ai_analysis TEXT")
            except sqlite3.OperationalError:
                pass
                
            try:
                conn.execute("ALTER TABLE context_entries ADD COLUMN concepts TEXT")
            except sqlite3.OperationalError:
                pass
                
            try:
                conn.execute("ALTER TABLE context_entries ADD COLUMN importance_score REAL DEFAULT 0.0")
            except sqlite3.OperationalError:
                pass
                
            try:
                conn.execute("ALTER TABLE context_entries ADD COLUMN memory_type TEXT DEFAULT 'temporary'")
            except sqlite3.OperationalError:
                pass
            
            # Now create the full schema (this will create tables if they don't exist)
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    context TEXT,
                    decision TEXT,
                    rationale TEXT,
                    alternatives TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    tags TEXT,
                    hash TEXT UNIQUE,
                    decision_type TEXT,
                    impact_areas TEXT,
                    confidence REAL DEFAULT 0.0,
                    ai_analysis TEXT
                );

                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    status TEXT DEFAULT 'pending',
                    priority TEXT DEFAULT 'medium',
                    context TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    completed_at DATETIME,
                    hash TEXT UNIQUE
                );

                CREATE TABLE IF NOT EXISTS patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    code_example TEXT,
                    use_cases TEXT,
                    category TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    hash TEXT UNIQUE
                );

                CREATE TABLE IF NOT EXISTS context_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tool_name TEXT,
                    command TEXT,
                    context TEXT,
                    result TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    session_id TEXT,
                    hash TEXT UNIQUE,
                    ai_analysis TEXT,
                    concepts TEXT,
                    importance_score REAL DEFAULT 0.0,
                    memory_type TEXT DEFAULT 'temporary'
                );

                CREATE TABLE IF NOT EXISTS concepts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    category TEXT,
                    description TEXT,
                    relationships TEXT,
                    importance_score REAL DEFAULT 0.0,
                    first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                    session_count INTEGER DEFAULT 1,
                    hash TEXT UNIQUE
                );

                CREATE INDEX IF NOT EXISTS idx_decisions_tags ON decisions(tags);
                CREATE INDEX IF NOT EXISTS idx_decisions_type ON decisions(decision_type);
                CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
                CREATE INDEX IF NOT EXISTS idx_patterns_category ON patterns(category);
                CREATE INDEX IF NOT EXISTS idx_context_tool ON context_entries(tool_name);
                CREATE INDEX IF NOT EXISTS idx_context_importance ON context_entries(importance_score);
                CREATE INDEX IF NOT EXISTS idx_concepts_category ON concepts(category);
                CREATE INDEX IF NOT EXISTS idx_concepts_importance ON concepts(importance_score);
            """)

    def _generate_hash(self, content: str) -> str:
        """Generate a hash for content deduplication."""
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def start_background_processing(self):
        """Start background processing loop."""
        if not self.ai_enabled:
            return
            
        def run_background_loop():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._background_task = self._loop.create_task(self._background_processor())
            self._loop.run_until_complete(self._background_task)
        
        thread = threading.Thread(target=run_background_loop, daemon=True)
        thread.start()

    async def _background_processor(self):
        """Background processor for AI analysis."""
        while True:
            try:
                # Wait for items to process
                item = await self._background_queue.get()
                if item is None:  # Shutdown signal
                    break
                    
                await self._process_background_item(item)
                self._background_queue.task_done()
                
                # Small delay to prevent overwhelming the API
                await asyncio.sleep(0.1)
                
            except Exception as e:
                print(f"Background processing error: {e}", file=sys.stderr)

    async def _process_background_item(self, item: dict):
        """Process a single background item with AI analysis."""
        try:
            analysis_type = item.get('type')
            data = item.get('data')
            
            if analysis_type == 'concept_extraction':
                await self._analyze_concepts_background(data)
            elif analysis_type == 'decision_analysis':
                await self._analyze_decision_background(data)
            elif analysis_type == 'contextual_memory':
                await self._analyze_memory_background(data)
                
        except Exception as e:
            print(f"Error processing background item: {e}", file=sys.stderr)

    async def _analyze_concepts_background(self, data: dict):
        """Analyze and extract concepts in background."""
        if not self.ai_enabled:
            return
            
        try:
            prompt = f"""
Tool: {data.get('tool_name', 'Unknown')}
Command/Context: {str(data.get('context', ''))[:1000]}
Session: {data.get('session_id', 'unknown')}

Extract and analyze key concepts from this development activity.
"""
            
            result = await self.concept_agent.run(prompt)
            concept_data = result.output
            
            # Store extracted concepts
            for concept in concept_data.concepts:
                self._store_concept(
                    name=concept,
                    category=concept_data.categories[0] if concept_data.categories else "general",
                    importance_score=concept_data.importance_score,
                    relationships=concept_data.relationships.get(concept, [])
                )
                
            # Update context entry with AI analysis
            self._update_context_entry_analysis(
                data.get('entry_id'),
                concepts=concept_data.concepts,
                importance_score=concept_data.importance_score,
                ai_analysis=concept_data.model_dump_json()
            )
            
        except Exception as e:
            print(f"Concept analysis error: {e}", file=sys.stderr)

    async def _analyze_decision_background(self, data: dict):
        """Analyze decisions in background using Kimi-K2 with reasoning and MCP client."""
        if not self.ai_enabled:
            return
            
        try:
            # Enhanced prompt for reasoning-capable Kimi-K2 model
            prompt = f"""
Development Activity Analysis:

Tool Used: {data.get('tool_name', 'Unknown')}
File Path: {data.get('file_path', 'N/A')}
Command/Action: {str(data.get('command', ''))[:500]}
Context: {str(data.get('context', ''))[:1000]}
Session: {data.get('session_id', 'unknown')}

Please analyze this development activity step by step:

1. First, reason about what type of development decision is being made here
2. Consider the context and patterns to determine confidence level
3. Think through potential impact areas and dependencies
4. Evaluate whether this decision should be stored for future reference
5. Assign appropriate priority based on importance and urgency

If you have access to Context Portal MCP tools, use them to:
- Check for related decisions (conport_search_decisions_fts)  
- Look up existing system patterns (conport_get_system_patterns)
- Search project glossary for relevant terms (conport_search_project_glossary_fts)

Use your reasoning capabilities to provide thoughtful analysis.
"""
            
            # Run decision analysis with MCP access
            async with self.decision_agent:
                result = await self.decision_agent.run(prompt)
                decision_data = result.output
                
                # Store reasoning information if available
                reasoning_info = ""
                if hasattr(result, 'thinking_parts') and result.thinking_parts:
                    reasoning_info = f"Reasoning: {result.thinking_parts[0].content[:500]}"
                
                if decision_data.recommended_storage:
                    # Store as a formal decision with reasoning
                    self.store_enhanced_decision(
                        title=f"AI-Detected Decision: {decision_data.decision_type} - {data.get('tool_name', 'Unknown')}",
                        description=str(data.get('context', ''))[:500],
                        decision_type=decision_data.decision_type,
                        confidence=decision_data.confidence,
                        impact_areas=decision_data.impact_areas,
                        ai_analysis=f"{decision_data.model_dump_json()}\n\n{reasoning_info}",
                        tags=[decision_data.decision_type, data.get('tool_name', 'unknown').lower()]
                    )
                    
                    print(f"Context Portal: Stored {decision_data.decision_type} decision with {decision_data.confidence:.2f} confidence", 
                          file=sys.stderr)
                
        except Exception as e:
            print(f"Decision analysis error: {e}", file=sys.stderr)

    async def _analyze_memory_background(self, data: dict):
        """Analyze contextual memory requirements in background."""
        if not self.ai_enabled:
            return
            
        try:
            prompt = f"""
Tool: {data.get('tool_name', 'Unknown')}
Context: {str(data.get('context', ''))[:1000]}
File Path: {data.get('file_path', 'N/A')}
Session: {data.get('session_id', 'unknown')}

Determine the memory characteristics of this development activity.
"""
            
            result = await self.memory_agent.run(prompt)
            memory_data = result.output
            
            # Update context entry with memory analysis
            if data.get('entry_id'):
                self._update_context_entry_memory_type(
                    data.get('entry_id'),
                    memory_data.memory_type,
                    memory_data.relevance_score
                )
                
        except Exception as e:
            print(f"Memory analysis error: {e}", file=sys.stderr)

    def queue_background_analysis(self, analysis_type: str, data: dict):
        """Queue an item for background AI analysis."""
        if not self.ai_enabled or not self._loop:
            return
            
        try:
            item = {'type': analysis_type, 'data': data}
            future = asyncio.run_coroutine_threadsafe(
                self._background_queue.put(item), 
                self._loop
            )
            # Don't wait for completion to avoid blocking
        except Exception as e:
            print(f"Error queuing background analysis: {e}", file=sys.stderr)

    def _store_concept(self, name: str, category: str, importance_score: float, relationships: list):
        """Store or update a concept."""
        content_hash = self._generate_hash(f"{name.lower()}{category}")
        relationships_json = json.dumps(relationships)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Check if concept exists
                cursor = conn.execute("SELECT id, session_count FROM concepts WHERE hash = ?", (content_hash,))
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing concept
                    conn.execute("""
                        UPDATE concepts 
                        SET last_updated = CURRENT_TIMESTAMP, 
                            session_count = ?,
                            importance_score = MAX(importance_score, ?),
                            relationships = ?
                        WHERE id = ?
                    """, (existing[1] + 1, importance_score, relationships_json, existing[0]))
                else:
                    # Insert new concept
                    conn.execute("""
                        INSERT INTO concepts 
                        (name, category, importance_score, relationships, hash)
                        VALUES (?, ?, ?, ?, ?)
                    """, (name, category, importance_score, relationships_json, content_hash))
                    
        except Exception as e:
            print(f"Error storing concept: {e}", file=sys.stderr)

    def store_enhanced_decision(self, title: str, description: str, decision_type: str = "unknown", 
                              confidence: float = 0.0, impact_areas: list = None, 
                              ai_analysis: str = "", tags: list = None) -> bool:
        """Store an enhanced decision with AI analysis."""
        impact_areas_str = ",".join(impact_areas or [])
        tags_str = ",".join(tags or [])
        content_hash = self._generate_hash(f"{title}{description}")

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO decisions
                    (title, description, decision_type, confidence, impact_areas, 
                     ai_analysis, tags, hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (title, description, decision_type, confidence, 
                      impact_areas_str, ai_analysis, tags_str, content_hash))
            return True
        except Exception as e:
            print(f"Error storing enhanced decision: {e}", file=sys.stderr)
            return False

    def store_enhanced_context_entry(self, tool_name: str, command: str, context: str = "",
                                   result: str = "", session_id: str = "", 
                                   file_path: str = "") -> Optional[int]:
        """Store a context entry and return its ID for background processing."""
        content_hash = self._generate_hash(f"{tool_name}{command}{context}")

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    INSERT OR REPLACE INTO context_entries
                    (tool_name, command, context, result, session_id, hash)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (tool_name, command, context, result, session_id, content_hash))
                entry_id = cursor.lastrowid
                
                # Queue for background analysis
                analysis_data = {
                    'entry_id': entry_id,
                    'tool_name': tool_name,
                    'command': command,
                    'context': context,
                    'session_id': session_id,
                    'file_path': file_path
                }
                
                # Queue multiple types of analysis
                self.queue_background_analysis('concept_extraction', analysis_data)
                self.queue_background_analysis('decision_analysis', analysis_data)
                self.queue_background_analysis('contextual_memory', analysis_data)
                
            return entry_id
        except Exception as e:
            print(f"Error storing enhanced context entry: {e}", file=sys.stderr)
            return None

    def _update_context_entry_analysis(self, entry_id: Optional[int], concepts: list, 
                                     importance_score: float, ai_analysis: str):
        """Update context entry with AI analysis results."""
        if not entry_id:
            return
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE context_entries 
                    SET concepts = ?, importance_score = ?, ai_analysis = ?
                    WHERE id = ?
                """, (json.dumps(concepts), importance_score, ai_analysis, entry_id))
        except Exception as e:
            print(f"Error updating context entry analysis: {e}", file=sys.stderr)

    def _update_context_entry_memory_type(self, entry_id: Optional[int], memory_type: str, 
                                        relevance_score: float):
        """Update context entry with memory type analysis."""
        if not entry_id:
            return
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE context_entries 
                    SET memory_type = ?
                    WHERE id = ?
                """, (memory_type, entry_id))
        except Exception as e:
            print(f"Error updating context entry memory type: {e}", file=sys.stderr)

    # Keep all existing methods for backward compatibility
    def store_decision(self, title: str, description: str = "", decision: str = "",
                      rationale: str = "", alternatives: str = "", tags: list = None) -> bool:
        """Store a basic decision (backward compatibility)."""
        return self.store_enhanced_decision(title, description, tags=tags)

    def store_task(self, title: str, description: str = "", status: str = "pending",
                  priority: str = "medium", context: str = "") -> bool:
        """Store a project task."""
        content_hash = self._generate_hash(f"{title}{description}{context}")

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO tasks
                    (title, description, status, priority, context, hash)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (title, description, status, priority, context, content_hash))
            return True
        except Exception as e:
            print(f"Error storing task: {e}", file=sys.stderr)
            return False

    def store_pattern(self, name: str, description: str = "", code_example: str = "",
                     use_cases: str = "", category: str = "") -> bool:
        """Store a code pattern."""
        content_hash = self._generate_hash(f"{name}{description}{code_example}")

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO patterns
                    (name, description, code_example, use_cases, category, hash)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (name, description, code_example, use_cases, category, content_hash))
            return True
        except Exception as e:
            print(f"Error storing pattern: {e}", file=sys.stderr)
            return False

    def search_decisions(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search for relevant decisions."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM decisions
                    WHERE title LIKE ? OR description LIKE ? OR decision LIKE ? OR tags LIKE ?
                    ORDER BY confidence DESC, timestamp DESC
                    LIMIT ?
                """, (f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%", limit))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error searching decisions: {e}", file=sys.stderr)
            return []

    def search_concepts(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search for concepts."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM concepts
                    WHERE name LIKE ? OR category LIKE ?
                    ORDER BY importance_score DESC, session_count DESC
                    LIMIT ?
                """, (f"%{query}%", f"%{query}%", limit))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error searching concepts: {e}", file=sys.stderr)
            return []

    def get_session_context(self, session_id: str, limit: int = 20) -> dict[str, Any]:
        """Get enhanced context for a session."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Get context entries for session
                cursor = conn.execute("""
                    SELECT * FROM context_entries
                    WHERE session_id = ?
                    ORDER BY importance_score DESC, timestamp DESC
                    LIMIT ?
                """, (session_id, limit))
                entries = [dict(row) for row in cursor.fetchall()]
                
                # Get related concepts
                cursor = conn.execute("""
                    SELECT DISTINCT c.* FROM concepts c
                    JOIN context_entries ce ON JSON_EXTRACT(ce.concepts, '$') LIKE '%' || c.name || '%'
                    WHERE ce.session_id = ?
                    ORDER BY c.importance_score DESC
                    LIMIT 10
                """, (session_id,))
                concepts = [dict(row) for row in cursor.fetchall()]
                
                return {
                    'entries': entries,
                    'concepts': concepts,
                    'ai_enabled': self.ai_enabled
                }
                
        except Exception as e:
            print(f"Error getting session context: {e}", file=sys.stderr)
            return {'entries': [], 'concepts': [], 'ai_enabled': self.ai_enabled}


class EnhancedContextPortalHook:
    """Enhanced hook with AI-powered background analysis."""

    def __init__(self):
        """Initialize the enhanced Context Portal hook."""
        self.memory_manager = EnhancedContextPortalMemoryManager()
        self.session_id = str(int(time.time()))
        
        # Start background processing
        self.memory_manager.start_background_processing()

        # Tools that should trigger context storage
        self.context_tools = {
            "Bash", "Edit", "Write", "Read", "Grep", "Glob", 
            "Task", "WebFetch", "WebSearch", "MultiEdit"
        }

        # Enhanced decision keywords
        self.decision_keywords = [
            "decide", "choose", "implement", "architecture", "design", "pattern",
            "approach", "solution", "fix", "refactor", "optimize", "migrate",
            "configure", "setup", "initialize", "deploy", "test", "debug"
        ]

    def should_process(self, tool_name: str, tool_input: dict[str, Any]) -> bool:
        """Determine if this tool usage should be processed."""
        return tool_name in self.context_tools

    def extract_enhanced_context_info(self, tool_name: str, tool_input: dict[str, Any]) -> dict[str, str]:
        """Extract enhanced context information from tool input."""
        context_info = {
            "tool": tool_name,
            "timestamp": datetime.now().isoformat(),
            "session": self.session_id,
        }

        # Extract tool-specific context with more detail
        if tool_name == "Bash":
            context_info["command"] = tool_input.get("command", "")
            context_info["description"] = tool_input.get("description", "")
            context_info["type"] = "command_execution"
        elif tool_name in ["Edit", "Write", "MultiEdit"]:
            context_info["file_path"] = tool_input.get("file_path", "")
            context_info["operation"] = tool_name.lower()
            context_info["type"] = "file_modification"
            # Try to extract file extension for context
            file_path = tool_input.get("file_path", "")
            if file_path:
                context_info["file_extension"] = Path(file_path).suffix
        elif tool_name == "Read":
            context_info["file_path"] = tool_input.get("file_path", "")
            context_info["operation"] = "read"
            context_info["type"] = "file_access"
        elif tool_name in ["Grep", "Glob"]:
            context_info["pattern"] = tool_input.get("pattern", "")
            context_info["path"] = tool_input.get("path", "")
            context_info["type"] = "search_operation"
        elif tool_name == "Task":
            context_info["description"] = tool_input.get("description", "")
            context_info["subagent_type"] = tool_input.get("subagent_type", "")
            context_info["type"] = "ai_task"
        elif tool_name in ["WebFetch", "WebSearch"]:
            context_info["url_or_query"] = tool_input.get("url", "") or tool_input.get("query", "")
            context_info["type"] = "web_operation"

        return context_info

    def detect_concept_introduction(self, tool_input: dict[str, Any]) -> list[str]:
        """Detect when new concepts are being introduced."""
        concepts = []
        text_content = " ".join(str(v) for v in tool_input.values()).lower()
        
        # Look for patterns that indicate concept introduction
        concept_patterns = [
            r"new (\w+)",
            r"create (\w+)",
            r"implement (\w+)",
            r"add (\w+)",
            r"introduce (\w+)",
            r"define (\w+)"
        ]
        
        import re
        for pattern in concept_patterns:
            matches = re.findall(pattern, text_content)
            concepts.extend(matches)
        
        return list(set(concepts))  # Remove duplicates

    def transform(self, tool_name: str, tool_input: dict[str, Any]) -> dict[str, Any] | None:
        """Transform tool input with enhanced AI analysis."""
        if not self.should_process(tool_name, tool_input):
            return None

        # Extract enhanced context information
        context_info = self.extract_enhanced_context_info(tool_name, tool_input)
        file_path = context_info.get("file_path", "")
        
        # Store context entry with background AI analysis
        entry_id = self.memory_manager.store_enhanced_context_entry(
            tool_name=tool_name,
            command=str(tool_input),
            context=json.dumps(context_info),
            session_id=self.session_id,
            file_path=file_path
        )

        # Detect concept introduction for immediate processing
        introduced_concepts = self.detect_concept_introduction(tool_input)
        if introduced_concepts:
            print(f"Context Portal: Detected new concepts: {', '.join(introduced_concepts)}", 
                  file=sys.stderr)

        # Check for decision context (immediate processing for important decisions)
        text_content = " ".join(str(v) for v in tool_input.values()).lower()
        for keyword in self.decision_keywords:
            if keyword in text_content:
                # Queue immediate decision analysis for important keywords
                if keyword in ["architecture", "design", "implement", "migrate"]:
                    print(f"Context Portal: Analyzing {keyword} decision in background", 
                          file=sys.stderr)
                break

        # Return None to indicate no immediate transformation
        # All analysis happens in background
        return None


def main():
    """Enhanced main hook entry point with background processing."""
    try:
        # Read JSON input from stdin
        input_data = json.loads(sys.stdin.read())

        # Extract fields
        session_id = input_data.get("session_id", "unknown")
        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})
        hook_event = input_data.get("hook_event_name", "")

        # Initialize enhanced hook
        hook = EnhancedContextPortalHook()
        hook.session_id = session_id

        if hook.should_process(tool_name, tool_input):
            # Process in background - don't block tool execution
            hook.transform(tool_name, tool_input)
            
            # For PreToolUse events, we can provide enhanced context
            if hook_event == "PreToolUse":
                session_context = hook.memory_manager.get_session_context(session_id, limit=5)
                if session_context['entries']:
                    print(f"Context Portal: Found {len(session_context['entries'])} related entries", 
                          file=sys.stderr)
                    
                    # Add context to tool input for user visibility
                    if session_context['concepts']:
                        concepts_summary = [c['name'] for c in session_context['concepts'][:3]]
                        print(f"Context Portal: Active concepts: {', '.join(concepts_summary)}", 
                              file=sys.stderr)

        # Always allow execution to proceed
        response = {"continue": True, "suppressOutput": False}
        print(json.dumps(response))

    except Exception as e:
        # Always fail-safe
        print(f"Enhanced Context Portal hook error: {str(e)}", file=sys.stderr)
        response = {"continue": True, "suppressOutput": False}
        print(json.dumps(response))


if __name__ == "__main__":
    main()