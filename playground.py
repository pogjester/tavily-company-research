import os
import asyncio
import cohere
from tavily import AsyncTavilyClient
from rich.console import Console
from rich.table import Table
from rich import print as rprint
import json
from typing import Dict, List, Any

console = Console()

class ScoringPlayground:
    def __init__(self):
        # Initialize API clients
        tavily_key = os.getenv("TAVILY_API_KEY")
        cohere_key = os.getenv("COHERE_API_KEY")
        
        if not tavily_key or not cohere_key:
            raise ValueError("Both TAVILY_API_KEY and COHERE_API_KEY must be set")
            
        self.tavily = AsyncTavilyClient(api_key=tavily_key)
        self.cohere = cohere.Client(cohere_key)
        
    def format_document(self, doc: Dict[str, Any]) -> str:
        """Format a document for Cohere evaluation."""
        parts = []
        if title := doc.get('title'):
            parts.append(f"Title: {title}")
        if content := doc.get('content', ''):
            # Truncate content if too long (Cohere has token limits)
            if len(content) > 1500:
                content = content[:1500] + "..."
            parts.append(f"Content: {content}")
        return "\n\n".join(parts)

    async def search_with_tavily(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Perform a search with Tavily and return results with scores."""
        try:
            response = await self.tavily.search(query, search_depth="advanced", max_results=max_results)
            return response.get('results', [])
        except Exception as e:
            console.print(f"[red]Error during Tavily search: {e}[/red]")
            return []

    async def rerank_with_cohere(self, query: str, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Rerank documents using Cohere and return scores."""
        try:
            # Format documents for Cohere
            formatted_docs = [self.format_document(doc) for doc in documents]
            
            # Get Cohere rankings
            response = self.cohere.rerank(
                model='rerank-v3.5',
                query=query,
                documents=formatted_docs,
                top_n=len(documents)
            )
            
            # Combine original documents with Cohere scores
            scored_docs = []
            for doc, result in zip(documents, response.results):
                scored_docs.append({
                    **doc,
                    'cohere_score': result.relevance_score
                })
            
            return scored_docs
        except Exception as e:
            console.print(f"[red]Error during Cohere reranking: {e}[/red]")
            return documents

    async def analyze_single_document(self, query: str, doc: Dict[str, Any]):
        """Analyze a single document with both Tavily and Cohere."""
        console.print(f"\n[cyan]Analyzing document:[/cyan] {doc.get('title', 'No title')[:100]}")
        console.print("[cyan]Content preview:[/cyan]", doc.get('content', '')[:200] + "...")
        
        # Get Cohere score for single document
        try:
            formatted_doc = self.format_document(doc)
            cohere_response = self.cohere.rerank(
                model='rerank-v3.5',
                query=query,
                documents=[formatted_doc],
                top_n=1
            )
            cohere_score = cohere_response.results[0].relevance_score
        except Exception as e:
            console.print(f"[red]Error getting Cohere score: {e}[/red]")
            cohere_score = 0

        # Get Tavily score
        tavily_score = float(doc.get('score', 0))

        # Display comparison
        analysis_table = Table(title="Single Document Analysis")
        analysis_table.add_column("Metric", style="cyan")
        analysis_table.add_column("Score", justify="right")
        
        analysis_table.add_row("Tavily Score", f"{tavily_score:.3f}")
        analysis_table.add_row("Cohere Score", f"{cohere_score:.3f}")
        
        # Calculate agreement/disagreement
        score_diff = abs(tavily_score - cohere_score)
        agreement = "High" if score_diff < 0.2 else "Medium" if score_diff < 0.4 else "Low"
        analysis_table.add_row("Score Difference", f"{score_diff:.3f}")
        analysis_table.add_row("Agreement Level", agreement)
        
        console.print(analysis_table)
        
        return {
            'title': doc.get('title'),
            'tavily_score': tavily_score,
            'cohere_score': cohere_score,
            'score_diff': score_diff,
            'agreement': agreement
        }

    def display_results(self, docs: List[Dict[str, Any]]):
        """Display comparison of Tavily and Cohere scores in a table."""
        table = Table(title="Document Scoring Comparison")
        
        table.add_column("Title", style="cyan", no_wrap=True)
        table.add_column("Tavily Score", justify="right", style="green")
        table.add_column("Cohere Score", justify="right", style="blue")
        table.add_column("Combined Score", justify="right", style="magenta")
        
        for doc in sorted(docs, key=lambda x: x.get('cohere_score', 0), reverse=True):
            tavily_score = float(doc.get('score', 0))
            cohere_score = float(doc.get('cohere_score', 0))
            # Calculate combined score (geometric mean)
            combined_score = (tavily_score * cohere_score) ** 0.5 if tavily_score and cohere_score else 0
            
            table.add_row(
                doc.get('title', 'No title')[:50] + "...",
                f"{tavily_score:.3f}",
                f"{cohere_score:.3f}",
                f"{combined_score:.3f}"
            )
        
        console.print(table)
        
        # Print statistics
        tavily_scores = [float(doc.get('score', 0)) for doc in docs]
        cohere_scores = [float(doc.get('cohere_score', 0)) for doc in docs]
        
        stats_table = Table(title="Scoring Statistics")
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Tavily", style="green")
        stats_table.add_column("Cohere", style="blue")
        
        stats_table.add_row(
            "Average Score",
            f"{sum(tavily_scores) / len(tavily_scores):.3f}",
            f"{sum(cohere_scores) / len(cohere_scores):.3f}"
        )
        stats_table.add_row(
            "Max Score",
            f"{max(tavily_scores):.3f}",
            f"{max(cohere_scores):.3f}"
        )
        stats_table.add_row(
            "Min Score",
            f"{min(tavily_scores):.3f}",
            f"{min(cohere_scores):.3f}"
        )
        
        console.print(stats_table)

    def save_results(self, docs: List[Dict[str, Any]], filename: str = "scoring_results.json"):
        """Save the scoring results to a JSON file."""
        try:
            with open(filename, 'w') as f:
                json.dump(docs, f, indent=2)
            console.print(f"[green]Results saved to {filename}[/green]")
        except Exception as e:
            console.print(f"[red]Error saving results: {e}[/red]")

async def main():
    # Test queries
    test_queries = [
        "What are Tavily's core products and features?",
        "What is Tavily's business model and pricing?",
        "Who are Tavily's main competitors?",
        "What makes Tavily different from other search APIs?"
    ]
    
    playground = ScoringPlayground()
    
    for query in test_queries:
        console.print(f"\n[yellow]Testing query: {query}[/yellow]")
        
        # Get initial results from Tavily
        tavily_results = await playground.search_with_tavily(query)
        if not tavily_results:
            continue
            
        # Rerank with Cohere
        scored_results = await playground.rerank_with_cohere(query, tavily_results)
        
        # Display and save batch results
        playground.display_results(scored_results)
        playground.save_results(scored_results, f"scoring_results_{query.replace(' ', '_')[:30]}.json")
        
        # Perform individual document analysis
        console.print("\n[yellow]Performing individual document analysis...[/yellow]")
        individual_analyses = []
        for doc in scored_results[:3]:  # Analyze top 3 documents
            analysis = await playground.analyze_single_document(query, doc)
            individual_analyses.append(analysis)
        
        # Save individual analyses
        with open(f"individual_analysis_{query.replace(' ', '_')[:30]}.json", 'w') as f:
            json.dump(individual_analyses, f, indent=2)

if __name__ == "__main__":
    asyncio.run(main()) 