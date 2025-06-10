# cli.py
import click
import inquirer
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from typing import List, Optional
import sys
import tkinter as tk
from tkinter import filedialog

from config import Config
from models import ProjectInfo, UploadedDocument, AnalysisRequest
from gemini_client import GeminiClient
from web_scraper import PolicyScraper
from report_generator import ReportGenerator

console = Console()

class ArchopinionCLI:
    def __init__(self):
        self.gemini_client = GeminiClient()
        self.scraper = PolicyScraper()
        self.report_generator = ReportGenerator()
        
    def display_welcome(self):
        """Display welcome message"""
        console.print(Panel.fit(
            "[bold green]ARCHOPINION[/bold green]\n"
            "AI Architectural Review Platform\n\n"
            "Get instant, expert-level analysis of your architectural projects",
            border_style="green"
        ))
        
    def get_project_info(self) -> ProjectInfo:
        """Collect project information"""
        console.print("\n[bold]Step 1: Project Information[/bold]")
        
        questions = [
            inquirer.Text('address', 
                         message="Project address",
                         validate=lambda _, x: len(x) > 0),
            inquirer.List('project_type',
                         message="Select project type",
                         choices=Config.PROJECT_TYPES),
            inquirer.Text('council',
                         message="Local planning authority (optional)",
                         default=""),
            inquirer.Text('planning_reference',
                         message="Previous planning reference (optional)", 
                         default="")
        ]
        
        answers = inquirer.prompt(questions)
        
        return ProjectInfo(
            address=answers['address'],
            project_type=answers['project_type'],
            council=answers['council'] or None,
            planning_reference=answers['planning_reference'] or None
        )
    
    def get_documents(self) -> List[UploadedDocument]:
        """Collect document uploads using file explorer"""
        console.print("\n[bold]Step 2: Document Upload[/bold]")
        documents = []
        
        # Create root window but hide it
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        root.attributes('-topmost', True)  # Bring to front
        
        while True:
            console.print("\n[cyan]Opening file selector...[/cyan]")
            
            # Open file dialog
            file_path = filedialog.askopenfilename(
                title="Select PDF file",
                filetypes=[
                    ("PDF files", "*.pdf"),
                    ("All files", "*.*")
                ],
                parent=root
            )
            
            # Check if user cancelled
            if not file_path:
                if documents:
                    console.print("[yellow]No file selected. Continuing with uploaded documents.[/yellow]")
                    break
                else:
                    console.print("[red]No files uploaded. Please select at least one file.[/red]")
                    continue
            
            file_path = Path(file_path)
            console.print(f"Selected: [green]{file_path.name}[/green]")
            
            # Auto-detect document type
            detected_type = self.auto_detect_document_type(file_path.name)
            
            # Select document type
            questions = [
                inquirer.List('document_type',
                             message="What type of document is this?",
                             choices=Config.DOCUMENT_TYPES,
                             default=detected_type)
            ]
            
            answers = inquirer.prompt(questions)
            
            # Upload to Gemini
            try:
                file_uri = self.gemini_client.upload_file(
                    file_path, 
                    f"{answers['document_type']} - {file_path.name}"
                )
                
                documents.append(UploadedDocument(
                    file_path=file_path,
                    document_type=answers['document_type'],
                    file_uri=file_uri
                ))
                
                # Show uploaded documents
                table = Table(title="Uploaded Documents")
                table.add_column("Type", style="cyan")
                table.add_column("Filename", style="green")
                table.add_column("Size", style="yellow")
                for doc in documents:
                    size_mb = doc.file_path.stat().st_size / (1024 * 1024)
                    table.add_row(doc.document_type, doc.file_path.name, f"{size_mb:.1f} MB")
                console.print(table)
                
            except Exception as e:
                console.print(f"[red]Error uploading file: {e}[/red]")
                continue
            
            # Ask if more documents
            more = inquirer.confirm("Upload another document?", default=False)
            if not more:
                break
        
        # Clean up tkinter
        root.destroy()
        
        if not documents:
            console.print("[red]No documents uploaded. Exiting.[/red]")
            sys.exit(1)
        
        # Verify uploads
        self.verify_uploads(documents)
        
        return documents
    
    def auto_detect_document_type(self, filename: str) -> str:
        """Auto-detect document type from filename"""
        filename_lower = filename.lower()
        
        if 'site' in filename_lower:
            return 'Site Plan'
        elif 'floor' in filename_lower and 'exist' in filename_lower:
            return 'Floor Plans - Existing'
        elif 'floor' in filename_lower and 'prop' in filename_lower:
            return 'Floor Plans - Proposed'
        elif 'elevation' in filename_lower and 'exist' in filename_lower:
            return 'Elevations - Existing'
        elif 'elevation' in filename_lower and 'prop' in filename_lower:
            return 'Elevations - Proposed'
        elif 'section' in filename_lower:
            return 'Sections'
        elif 'design' in filename_lower or 'access' in filename_lower:
            return 'Design & Access Statement'
        elif 'plan' in filename_lower:
            return 'Site Plan'
        else:
            return 'Other Supporting Documents'
    
    def verify_uploads(self, documents: List[UploadedDocument]):
        """Verify that files were uploaded correctly"""
        console.print("\n[dim]Verifying uploads...[/dim]")
        
        all_verified = True
        for doc in documents:
            if doc.file_uri:
                file_info = self.gemini_client.get_file_info(doc.file_uri)
                if 'error' not in file_info:
                    size_mb = file_info.get('size_bytes', 0) / (1024 * 1024)
                    console.print(f"[green]✓[/green] {doc.document_type}: {size_mb:.1f} MB verified")
                else:
                    console.print(f"[yellow]⚠[/yellow] {doc.document_type}: Verification failed")
                    all_verified = False
        
        if all_verified:
            console.print("[green]All files verified successfully![/green]")
        else:
            console.print("[yellow]Some files could not be verified but analysis will continue[/yellow]")
    
    def get_frameworks(self) -> List[str]:
        """Select regulatory frameworks"""
        console.print("\n[bold]Step 3: Select Regulatory Frameworks[/bold]")
        
        # Create choices with descriptions
        choices = []
        for code, name in Config.PLANNING_FRAMEWORKS.items():
            choices.append((f"{code} - {name}", code))
        
        questions = [
            inquirer.Checkbox('frameworks',
                            message="Select frameworks to analyze against (Space to select, Enter to confirm)",
                            choices=choices,
                            default=['NPPF', 'PDR'])
        ]
        
        answers = inquirer.prompt(questions)
        
        if not answers['frameworks']:
            console.print("[yellow]No frameworks selected. Using NPPF as default.[/yellow]")
            return ['NPPF']
            
        return answers['frameworks']
    
    def get_user_prompt(self) -> str:
        """Get the user's analysis prompt"""
        console.print("\n[bold]Step 4: Analysis Instructions[/bold]")
        
        default_prompt = "Please review these drawings for compliance with all selected planning policies and building regulations."
        
        questions = [
            inquirer.Text('prompt',
                         message="Describe what you want the AI to analyze",
                         default=default_prompt,
                         validate=lambda _, x: len(x) > 10)
        ]
        
        answers = inquirer.prompt(questions)
        return answers['prompt']
    
    def run(self):
        """Main CLI workflow"""
        self.display_welcome()
        
        try:
            # Test API connection first
            if not self.gemini_client.test_connection():
                console.print("[red]Cannot connect to Gemini API. Please check your API key.[/red]")
                return
            
            # Collect all inputs
            project_info = self.get_project_info()
            documents = self.get_documents()
            frameworks = self.get_frameworks()
            user_prompt = self.get_user_prompt()
            
            # Create analysis request
            request = AnalysisRequest(
                project_info=project_info,
                documents=documents,
                selected_frameworks=frameworks,
                user_prompt=user_prompt
            )
            
            # Show summary
            console.print("\n[bold]Analysis Summary:[/bold]")
            console.print(f"Address: {project_info.address}")
            console.print(f"Project Type: {project_info.project_type}")
            console.print(f"Documents: {len(documents)} uploaded")
            console.print(f"Frameworks: {', '.join(frameworks)}")
            
            # Confirm
            if not inquirer.confirm("\nProceed with analysis?", default=True):
                console.print("[yellow]Analysis cancelled.[/yellow]")
                # Cleanup uploaded files
                self.gemini_client.cleanup_files(documents)
                return
            
            # Fetch framework content
            console.print("\n[bold]Fetching regulatory frameworks...[/bold]")
            frameworks_content = self.scraper.get_council_policies(
                project_info.council or "Local",
                frameworks
            )
            
            # Run analysis
            console.print("\n[bold]Running AI analysis...[/bold]")
            try:
                analysis_result = self.gemini_client.analyze(request, frameworks_content)
            except Exception as e:
                console.print(f"[red]Analysis failed: {e}[/red]")
                # Cleanup uploaded files
                self.gemini_client.cleanup_files(documents)
                return
            
            # Generate report
            console.print("\n[bold]Generating report...[/bold]")
            try:
                report_path = self.report_generator.generate_report(request, analysis_result)
                
                # Success message
                console.print(Panel.fit(
                    f"[bold green]✓ Analysis Complete![/bold green]\n\n"
                    f"Report saved to:\n[cyan]{report_path}[/cyan]",
                    border_style="green"
                ))
                
                # Offer to open the report
                if inquirer.confirm("\nOpen the report now?", default=True):
                    import os
                    import platform
                    
                    if platform.system() == 'Windows':
                        os.startfile(report_path)
                    elif platform.system() == 'Darwin':  # macOS
                        os.system(f'open "{report_path}"')
                    else:  # Linux
                        os.system(f'xdg-open "{report_path}"')
                
            except Exception as e:
                console.print(f"[red]Report generation failed: {e}[/red]")
            
            finally:
                # Always cleanup uploaded files
                console.print("\n[dim]Cleaning up...[/dim]")
                self.gemini_client.cleanup_files(documents)
                
        except KeyboardInterrupt:
            console.print("\n[yellow]Analysis cancelled by user.[/yellow]")
            # Cleanup any uploaded files
            if 'documents' in locals():
                self.gemini_client.cleanup_files(documents)
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]")
            # Cleanup any uploaded files
            if 'documents' in locals():
                self.gemini_client.cleanup_files(documents)
            raise

@click.command()
@click.option('--test', is_flag=True, help='Run in test mode with mock data')
@click.option('--debug', is_flag=True, help='Enable debug output')
def main(test, debug):
    """Archopinion - AI Architectural Review Platform"""
    cli = ArchopinionCLI()
    
    if debug:
        import logging
        logging.basicConfig(level=logging.DEBUG)
        console.print("[yellow]Debug mode enabled[/yellow]")
    
    if test:
        console.print("[yellow]Running in test mode[/yellow]")
        # You can add test mode logic here
    
    cli.run()

if __name__ == "__main__":
    main()