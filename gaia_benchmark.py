"""
GAIA Full Benchmark Test - Run complete validation set
"""

import os
import json
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import re

from manager import ManagerAgent
from config import Config, ConfigManager
from langchain.tools import Tool


class GAIABenchmarkRunner:
    """Run full GAIA benchmark"""

    def __init__(self):
        self.results = []
        self.start_time = None

    def load_gaia_jsonl(self, filepath: str) -> List[Dict]:
        """Load JSONL file"""
        tasks = []

        print(f"Loading GAIA dataset from: {filepath}")

        with open(filepath, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    obj = json.loads(line)
                    task = {
                        'task_id': obj.get('task_id', f'task_{line_num}'),
                        'question': obj.get('Question', ''),
                        'answer': obj.get('Final answer', ''),
                        'level': int(obj.get('Level', 1)),
                        'file_name': obj.get('file_name', None)
                    }

                    if task['question']:
                        tasks.append(task)

                except json.JSONDecodeError as e:
                    print(f"Error parsing line {line_num}: {e}")
                    continue

        return tasks

    def create_gaia_agent(self) -> ManagerAgent:
        """Create agent with GAIA tools"""
        config = Config(topic="GAIA_Benchmark")
        ConfigManager.set_config(config)

        manager = ManagerAgent()

        # Add calculator tool
        def calculator(expression: str) -> str:
            try:
                # Safe evaluation with common math functions
                allowed = {
                    "abs": abs, "round": round, "pow": pow,
                    "min": min, "max": max, "sum": sum,
                    "int": int, "float": float, "len": len,
                    "sqrt": lambda x: x**0.5,
                    "pi": 3.14159265359,
                    "e": 2.71828182846
                }
                result = eval(expression, {"__builtins__": {}}, allowed)
                return str(result)
            except Exception as e:
                return f"Calculation error: {str(e)}"

        calc_tool = Tool(
            name="calculator",
            description="Perform mathematical calculations. Input: mathematical expression",
            func=calculator
        )

        # Add file reader tool (for GAIA tasks with files)
        def read_file(filename: str) -> str:
            try:
                # Check in GAIA files directory
                gaia_files_dir = "./gaia_dataset/files"
                filepath = os.path.join(gaia_files_dir, filename)

                if not os.path.exists(filepath):
                    # Try validation/test subdirectories
                    for subdir in ["validation", "test"]:
                        alt_path = os.path.join("./gaia_dataset", subdir, "files", filename)
                        if os.path.exists(alt_path):
                            filepath = alt_path
                            break

                if os.path.exists(filepath):
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    return content[:5000]  # Limit size
                else:
                    return f"File not found: {filename}"

            except Exception as e:
                return f"Error reading file: {str(e)}"

        file_tool = Tool(
            name="read_file",
            description="Read contents of a file. Input: filename",
            func=read_file
        )

        # Add tools to manager
        manager.tools.extend([calc_tool, file_tool])
        manager.agent_executor = manager._create_agent_executor()

        return manager

    def extract_answer(self, output: str) -> str:
        """Extract final answer from agent output"""
        # Try different patterns
        patterns = [
            r"Final Answer:\s*(.+?)(?:\n|$)",
            r"The answer is:\s*(.+?)(?:\n|$)",
            r"Therefore,?\s*(.+?)(?:\n|$)",
            r"Answer:\s*(.+?)(?:\n|$)"
        ]

        for pattern in patterns:
            match = re.search(pattern, output, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()

        # If no pattern, try to get the last meaningful line
        lines = output.strip().split('\n')
        for line in reversed(lines):
            line = line.strip()
            if line and not any(line.startswith(prefix) for prefix in ['Thought:', 'Action:', 'Observation:']):
                return line

        return output.strip()

    def normalize_answer(self, answer: str) -> str:
        """Normalize answer for comparison"""
        if not answer:
            return ""

        # Convert to lowercase and strip
        answer = str(answer).lower().strip()

        # Remove trailing punctuation
        answer = answer.rstrip('.,!?;:')

        # Handle numbers
        try:
            # Try to parse as number
            num = float(answer.replace(',', ''))
            # Format consistently
            if num.is_integer():
                return str(int(num))
            else:
                # Round to reasonable precision
                return f"{num:.6f}".rstrip('0').rstrip('.')
        except:
            pass

        return answer

    def check_answer(self, predicted: str, expected: str) -> bool:
        """Check if answer is correct"""
        pred_norm = self.normalize_answer(predicted)
        exp_norm = self.normalize_answer(expected)

        # Exact match
        if pred_norm == exp_norm:
            return True

        # Check if expected answer is contained in prediction
        if exp_norm in pred_norm:
            return True

        # For yes/no questions
        if exp_norm in ['yes', 'no']:
            if exp_norm in pred_norm:
                return True

        # For numerical answers, allow small differences
        try:
            pred_num = float(pred_norm)
            exp_num = float(exp_norm)
            # Allow 0.01% difference
            if abs(pred_num - exp_num) / max(abs(exp_num), 1) < 0.0001:
                return True
        except:
            pass

        return False

    def run_benchmark(self, tasks: List[Dict], max_tasks: int = None, start_from: int = 0):
        """Run GAIA benchmark on tasks"""

        if max_tasks:
            tasks = tasks[start_from:start_from + max_tasks]
        else:
            tasks = tasks[start_from:]

        print(f"\n{'='*60}")
        print(f"Running GAIA Benchmark on {len(tasks)} tasks")
        print(f"{'='*60}\n")

        # Create agent
        agent = self.create_gaia_agent()

        # Statistics
        correct_by_level = {1: 0, 2: 0, 3: 0}
        total_by_level = {1: 0, 2: 0, 3: 0}

        self.start_time = time.time()

        for i, task in enumerate(tasks):
            task_start = time.time()

            print(f"\nTask {i+1}/{len(tasks)} - ID: {task['task_id']} (Level {task['level']})")
            print(f"Question: {task['question'][:150]}{'...' if len(task['question']) > 150 else ''}")

            # Add file info if present
            input_text = task['question']
            if task.get('file_name'):
                input_text += f"\n\nNote: A file '{task['file_name']}' is available. Use read_file('{task['file_name']}') to access it."

            try:
                # Run agent with timeout
                result = agent.agent_executor.invoke(
                    {"input": input_text},
                    {"timeout": 120}  # 2 minute timeout per task
                )

                output = result.get("output", "")
                predicted = self.extract_answer(output)

                print(f"Predicted: {predicted}")
                print(f"Expected: {task['answer']}")

                # Check answer
                is_correct = self.check_answer(predicted, task['answer'])

                print(f"Result: {'✓ CORRECT' if is_correct else '✗ INCORRECT'}")

                # Update statistics
                level = task['level']
                total_by_level[level] += 1
                if is_correct:
                    correct_by_level[level] += 1

                # Store result
                self.results.append({
                    'task_id': task['task_id'],
                    'level': task['level'],
                    'question': task['question'],
                    'predicted': predicted,
                    'expected': task['answer'],
                    'correct': is_correct,
                    'time': time.time() - task_start,
                    'output_length': len(output)
                })

            except Exception as e:
                print(f"Error: {e}")

                total_by_level[task['level']] += 1

                self.results.append({
                    'task_id': task['task_id'],
                    'level': task['level'],
                    'question': task['question'],
                    'predicted': None,
                    'expected': task['answer'],
                    'correct': False,
                    'error': str(e),
                    'time': time.time() - task_start
                })

            # Progress update every 10 tasks
            if (i + 1) % 10 == 0:
                elapsed = time.time() - self.start_time
                rate = (i + 1) / elapsed
                remaining = (len(tasks) - i - 1) / rate
                print(f"\nProgress: {i+1}/{len(tasks)} tasks completed")
                print(f"Time elapsed: {elapsed:.1f}s, Estimated remaining: {remaining:.1f}s")

                # Current accuracy
                total_correct = sum(correct_by_level.values())
                total_done = sum(total_by_level.values())
                if total_done > 0:
                    print(f"Current accuracy: {total_correct}/{total_done} ({total_correct/total_done*100:.1f}%)")

        # Final statistics
        total_correct = sum(correct_by_level.values())
        total_tasks = sum(total_by_level.values())

        print(f"\n{'='*60}")
        print("GAIA BENCHMARK RESULTS")
        print(f"{'='*60}")
        print(f"Overall Accuracy: {total_correct}/{total_tasks} ({total_correct/total_tasks*100:.1f}%)")

        for level in [1, 2, 3]:
            if total_by_level[level] > 0:
                acc = correct_by_level[level] / total_by_level[level] * 100
                print(f"Level {level}: {correct_by_level[level]}/{total_by_level[level]} ({acc:.1f}%)")

        # Save results
        output_file = f"gaia_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump({
                'summary': {
                    'total_tasks': total_tasks,
                    'total_correct': total_correct,
                    'accuracy': total_correct/total_tasks if total_tasks > 0 else 0,
                    'by_level': {
                        level: {
                            'correct': correct_by_level[level],
                            'total': total_by_level[level],
                            'accuracy': correct_by_level[level]/total_by_level[level] if total_by_level[level] > 0 else 0
                        }
                        for level in [1, 2, 3]
                    },
                    'runtime_seconds': time.time() - self.start_time
                },
                'results': self.results
            }, f, indent=2)

        print(f"\nDetailed results saved to: {output_file}")

        # Cleanup
        ConfigManager.clear_config()

        return total_correct / total_tasks if total_tasks > 0 else 0


def main():
    """Run full GAIA benchmark"""
    import argparse

    parser = argparse.ArgumentParser(description='Run GAIA Benchmark')
    parser.add_argument('--max-tasks', type=int, help='Maximum number of tasks to run (for testing)')
    parser.add_argument('--start-from', type=int, default=0, help='Start from task number')
    parser.add_argument('--level', type=int, choices=[1, 2, 3], help='Run only specific level')
    parser.add_argument('--file', type=str, default='./gaia_dataset/validation/metadata.jsonl', help='Path to GAIA JSONL file')

    args = parser.parse_args()

    # Check if file exists
    if not os.path.exists(args.file):
        print(f"File not found: {args.file}")
        print("\nSearching for GAIA files...")

        for root, dirs, files in os.walk("./gaia_dataset"):
            for file in files:
                if file.endswith('.jsonl'):
                    print(f"Found: {os.path.join(root, file)}")

        return

    # Run benchmark
    runner = GAIABenchmarkRunner()

    # Load tasks
    all_tasks = runner.load_gaia_jsonl(args.file)
    print(f"Loaded {len(all_tasks)} tasks total")

    # Filter by level if specified
    if args.level:
        tasks = [t for t in all_tasks if t['level'] == args.level]
        print(f"Filtered to {len(tasks)} level {args.level} tasks")
    else:
        tasks = all_tasks

    # Check Ollama
    import requests
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code != 200:
            print("\nERROR: Ollama is not running!")
            return
    except:
        print("\nERROR: Cannot connect to Ollama!")
        return

    # Run benchmark
    accuracy = runner.run_benchmark(tasks, args.max_tasks, args.start_from)

    print(f"\nBenchmark complete! Overall accuracy: {accuracy*100:.1f}%")


if __name__ == "__main__":
    main()