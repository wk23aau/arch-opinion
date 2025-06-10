# gemini_client.py
import google.generativeai as genai
from typing import List, Dict, Optional
import json
import time
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from google.api_core import exceptions
from datetime import datetime

from config import Config
from models import AnalysisRequest, UploadedDocument

console = Console()

class GeminiClient:
    def __init__(self):
        if not Config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        genai.configure(api_key=Config.GEMINI_API_KEY)
        
        # Use configurable model with fallback
        model_name = getattr(Config, 'GEMINI_MODEL', 'gemini-2.0-flash-exp')
        try:
            self.model = genai.GenerativeModel(model_name)
            console.print(f"[cyan]Using model: {model_name}[/cyan]")
        except Exception as e:
            console.print(f"[yellow]Failed to load {model_name}, falling back to gemini-1.5-flash[/yellow]")
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Rate limiting configuration
        self.max_retries = getattr(Config, 'MAX_RETRIES', 3)
        self.base_retry_delay = getattr(Config, 'RATE_LIMIT_DELAY', 10)
        
    def wait_with_backoff(self, attempt: int, base_delay: int, error: Optional[Exception] = None) -> int:
        """Calculate and wait with exponential backoff"""
        # Try to extract retry delay from error if available
        if error and hasattr(error, '_details'):
            try:
                # Parse the error details to find retry_delay
                details = str(error._details)
                if 'retry_delay' in details:
                    import re
                    match = re.search(r'seconds:\s*(\d+)', details)
                    if match:
                        base_delay = int(match.group(1))
            except:
                pass
        
        # Calculate exponential backoff
        delay = base_delay * (2 ** attempt)
        
        console.print(f"[yellow]⏳ Rate limit hit. Waiting {delay} seconds before retry (attempt {attempt + 1}/{self.max_retries})...[/yellow]")
        
        # Show countdown
        for remaining in range(delay, 0, -1):
            console.print(f"[dim]   Resuming in {remaining} seconds...[/dim]", end='\r')
            time.sleep(1)
        
        console.print(" " * 50, end='\r')  # Clear the countdown line
        return delay
        
    def upload_file(self, file_path: Path, display_name: str) -> str:
        """Upload file to Google File API and return URI with retry logic"""
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console,
                    transient=True
                ) as progress:
                    task = progress.add_task(f"Uploading {display_name}...", total=None)
                    
                    file = genai.upload_file(path=str(file_path), display_name=display_name)
                    
                    # Wait for file to be ready
                    while file.state.name == "PROCESSING":
                        time.sleep(2)
                        file = genai.get_file(file.name)
                        
                    if file.state.name == "FAILED":
                        raise ValueError(f"File upload failed: {file.state.name}")
                
                console.print(f"[green]✓[/green] Uploaded: {display_name}")
                return file.uri
                
            except exceptions.ResourceExhausted as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    self.wait_with_backoff(attempt, self.base_retry_delay, e)
                else:
                    console.print(f"[red]❌ Failed to upload after {self.max_retries} attempts[/red]")
                    raise
                    
            except Exception as e:
                console.print(f"[red]Error uploading file: {e}[/red]")
                raise
    
    def build_master_prompt(self, request: AnalysisRequest, 
                          frameworks_content: Dict[str, str]) -> str:
        """Construct the master prompt for Gemini"""
        
        # Document references
        doc_refs = "\n".join([
            f"- {doc.document_type}: {doc.file_uri}" 
            for doc in request.documents
        ])
        
        # Frameworks content (optimized for token limits)
        frameworks_text = ""
        for name, content in frameworks_content.items():
            max_framework_length = 1000  # Balanced for good context
            if len(content) > max_framework_length:
                content = content[:max_framework_length] + "\n[Content truncated]"
            frameworks_text += f"\n**{name}:**\n{content}\n"
        
        prompt = f"""
You are an expert AI Planning Consultant analyzing architectural drawings for UK planning compliance.

PROJECT: {request.project_info.project_type}
ADDRESS: {request.project_info.address}
AUTHORITY: {request.project_info.council or 'Not specified'}
{f'PREVIOUS PLANNING REF: {request.project_info.planning_reference}' if request.project_info.planning_reference else ''}

UPLOADED FILES:
{doc_refs}

INSTRUCTIONS:
1. EXAMINE each page of the PDF carefully
2. IDENTIFY all architectural drawings (plans, elevations, sections, site plans)
3. READ dimensions, annotations, and labels
4. ANALYZE for compliance with UK planning regulations

WHAT TO LOOK FOR:
- Building dimensions (height, width, depth)
- Extension sizes and setbacks
- Relationship to boundaries and neighbors
- Materials and design features
- Any text annotations or notes

REGULATIONS TO CHECK:
{frameworks_text}

USER REQUEST:
{request.user_prompt}

OUTPUT FORMAT - Provide a JSON object with:
{{
  "aiReviewFramework": [
    {{
      "framework": "Framework name",
      "relevantPolicies": ["List specific policies"],
      "keyConsiderations": "How this framework applies to the drawings"
    }}
  ],
  "planByPlanReview": [
    {{
      "planType": "Drawing title/type from the PDF",
      "positives": ["Good aspects observed"],
      "observations": ["Concerns or issues"],
      "complianceNotes": "Specific measurements and compliance details"
    }}
  ],
  "policyCompatibilitySummary": [
    {{
      "policyArea": "Area of concern",
      "status": "Compliant/Partially Compliant/Non-Compliant",
      "details": "Explanation with specific references to drawings",
      "recommendations": ["Actions needed"]
    }}
  ],
  "aiRecommendationSummary": "Overall assessment with specific references to the drawings analyzed"
}}

Base your analysis on the ACTUAL content visible in the PDFs.
"""
        return prompt
    
    def analyze(self, request: AnalysisRequest, 
                frameworks_content: Dict[str, str]) -> Dict:
        """Send analysis request to Gemini and parse response with retry logic"""
        
        # Build the text prompt
        text_prompt = self.build_master_prompt(request, frameworks_content)
        
        # Log token estimate
        token_estimate = len(text_prompt.split()) * 1.3  # Rough estimate
        console.print(f"[dim]Estimated tokens: ~{int(token_estimate)}[/dim]")
        
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console,
                    transient=True
                ) as progress:
                    task = progress.add_task("Analyzing architectural drawings...", total=None)
                    
                    start_time = time.time()
                    
                    # IMPORTANT: Pass the prompt as plain text
                    # Gemini will automatically process the file URIs in the prompt
                    response = self.model.generate_content(text_prompt)
                    
                    elapsed_time = time.time() - start_time
                    
                console.print(f"[dim]Analysis completed in {elapsed_time:.1f} seconds[/dim]")
                
                # Extract JSON from response
                response_text = response.text
                
                # Debug: Show if we got a response
                if response_text:
                    console.print("[dim]Received response from Gemini[/dim]")
                
                # Try to find JSON in the response
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                
                if start_idx == -1 or end_idx == 0:
                    # If no JSON found, try to request it again with a simpler prompt
                    if attempt < self.max_retries - 1:
                        console.print("[yellow]No JSON found in response. Retrying...[/yellow]")
                        time.sleep(5)
                        continue
                    else:
                        # Log the response for debugging
                        console.print(f"[red]Response without JSON:[/red]")
                        console.print(response_text[:500])
                        raise ValueError("No valid JSON found in response after retries")
                        
                json_str = response_text[start_idx:end_idx]
                
                try:
                    result = json.loads(json_str)
                    console.print("[green]✓[/green] Analysis complete")
                    return result
                except json.JSONDecodeError as e:
                    if attempt < self.max_retries - 1:
                        console.print(f"[yellow]JSON parsing error. Retrying...[/yellow]")
                        time.sleep(5)
                        continue
                    else:
                        console.print(f"[red]Error parsing JSON: {e}[/red]")
                        console.print(f"[dim]Attempted to parse: {json_str[:200]}...[/dim]")
                        raise ValueError(f"Invalid JSON response: {e}")
                        
            except exceptions.ResourceExhausted as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    self.wait_with_backoff(attempt, self.base_retry_delay, e)
                else:
                    console.print("[red]❌ Rate limit exceeded after all retries.[/red]")
                    console.print("[yellow]Suggestions:[/yellow]")
                    console.print("  • Wait a few minutes and try again")
                    console.print("  • Switch to gemini-2.0-flash-exp model in .env")
                    console.print("  • Reduce the number of frameworks selected")
                    console.print("  • Upgrade to a paid API plan")
                    raise
                    
            except exceptions.InvalidArgument as e:
                console.print(f"[red]Invalid request: {e}[/red]")
                raise
                
            except Exception as e:
                last_error = e
                console.print(f"[red]Unexpected error: {type(e).__name__}: {e}[/red]")
                if attempt < self.max_retries - 1:
                    console.print(f"[yellow]Retrying in 5 seconds...[/yellow]")
                    time.sleep(5)
                else:
                    raise
        
        # If we get here, all retries failed
        if last_error:
            raise last_error
        else:
            raise ValueError("Analysis failed after all retries")
    
    def build_simplified_prompt(self, request: AnalysisRequest) -> str:
        """Build a simplified prompt for retry attempts"""
        doc_refs = ", ".join([doc.document_type for doc in request.documents])
        
        prompt = f"""
Analyze the uploaded architectural PDFs for a {request.project_info.project_type} at {request.project_info.address}.

Documents: {doc_refs}

IMPORTANT: Look at ALL pages and drawings in the PDFs. Identify floor plans, elevations, sections, and site plans.

Provide a JSON response with these keys only:
- aiReviewFramework: array of framework analysis
- planByPlanReview: array of plan reviews  
- policyCompatibilitySummary: array of policy summaries
- aiRecommendationSummary: string with recommendations

Keep responses concise. Output valid JSON only.
"""
        return prompt
    
    def test_connection(self) -> bool:
        """Test the API connection with a simple request"""
        try:
            console.print("[cyan]Testing Gemini API connection...[/cyan]")
            response = self.model.generate_content("Hello, please respond with 'Connection successful'")
            if response.text:
                console.print("[green]✓[/green] API connection successful")
                return True
        except exceptions.ResourceExhausted:
            console.print("[red]❌ API quota exceeded[/red]")
            return False
        except Exception as e:
            console.print(f"[red]❌ API connection failed: {e}[/red]")
            return False
    
    def test_vision_capability(self, file_uri: str) -> str:
        """Test what Gemini can see in a file"""
        try:
            console.print("[cyan]Testing vision capability...[/cyan]")
            
            # Simple vision test prompt
            test_prompt = f"""
Look at this PDF and tell me:
1. How many pages does it have?
2. What types of drawings can you see?
3. Can you read any text or dimensions?
4. Describe what you see on the first page.

File: {file_uri}

Be specific about what visual elements you can identify.
"""
            
            response = self.model.generate_content(test_prompt)
            return response.text
            
        except Exception as e:
            return f"Vision test failed: {e}"
    
    def get_file_info(self, file_uri: str) -> Dict:
        """Get information about an uploaded file"""
        try:
            # Extract file name from URI
            file_name = file_uri.split('/')[-1]
            file = genai.get_file(file_name)
            return {
                "name": file.name,
                "display_name": file.display_name,
                "mime_type": file.mime_type,
                "size_bytes": file.size_bytes,
                "state": file.state.name,
                "uri": file.uri
            }
        except Exception as e:
            console.print(f"[yellow]Warning: Could not get file info: {e}[/yellow]")
            return {"uri": file_uri, "error": str(e)}
    
    def delete_uploaded_file(self, file_uri: str) -> bool:
        """Delete an uploaded file from Google's servers"""
        try:
            file_name = file_uri.split('/')[-1]
            genai.delete_file(file_name)
            console.print(f"[dim]Deleted uploaded file: {file_name}[/dim]")
            return True
        except Exception as e:
            console.print(f"[yellow]Warning: Could not delete file: {e}[/yellow]")
            return False
    
    def cleanup_files(self, documents: List[UploadedDocument]):
        """Clean up all uploaded files"""
        console.print("[dim]Cleaning up uploaded files...[/dim]")
        for doc in documents:
            if doc.file_uri:
                self.delete_uploaded_file(doc.file_uri)