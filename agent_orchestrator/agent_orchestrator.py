            self.agents[task.agent_name]['last_run'] = datetime.now()
            self._calculate_next_run(task.agent_name)
            
            self.logger.info(f"Task {task.id} completed successfully")
            
        except Exception as e:
            # Handle execution error
            task.status = AgentStatus.ERROR
            task.completed_at = datetime.now()
            task.error = str(e)
            
            # Update agent metrics
            self._update_agent_metrics(task.agent_name, success=False)
            
            self.logger.error(f"Task {task.id} failed: {e}")
        
        finally:
            # Save task
            self._save_task(task)
            
            # Move from active to completed
            if task.id in self.active_tasks:
                del self.active_tasks[task.id]
            
            self.completed_tasks.append(task)
            
            # Limit completed tasks history
            if len(self.completed_tasks) > 100:
                self.completed_tasks = self.completed_tasks[-100:]
    
    def _update_agent_metrics(self, agent_name: str, success: bool, execution_time: float = 0.0):
        """Update agent performance metrics."""
        if agent_name not in self.agent_metrics:
            self.agent_metrics[agent_name] = AgentMetrics(agent_name=agent_name)
        
        metrics = self.agent_metrics[agent_name]
        metrics.total_tasks += 1
        
        if success:
            metrics.completed_tasks += 1
        else:
            metrics.failed_tasks += 1
        
        # Update average execution time
        if execution_time > 0:
            if metrics.avg_execution_time == 0:
                metrics.avg_execution_time = execution_time
            else:
                metrics.avg_execution_time = (metrics.avg_execution_time * (metrics.total_tasks - 1) + execution_time) / metrics.total_tasks
        
        metrics.last_execution = datetime.now()
        metrics.success_rate = metrics.completed_tasks / metrics.total_tasks if metrics.total_tasks > 0 else 0
        
        # Save metrics
        self._save_agent_metrics(agent_name)
    
    def _save_agent_metrics(self, agent_name: str):
        """Save agent metrics to disk."""
        metrics_file = os.path.join(self.shared_data_path, "orchestrator", "metrics", 
                                   f"metrics_{agent_name}.json")
        
        try:
            metrics = self.agent_metrics[agent_name]
            metrics_dict = asdict(metrics)
            
            # Convert datetime to ISO format
            if metrics_dict['last_execution']:
                metrics_dict['last_execution'] = metrics_dict['last_execution'].isoformat()
            
            with open(metrics_file, 'w', encoding='utf-8') as f:
                json.dump(metrics_dict, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Failed to save metrics for {agent_name}: {e}")
    
    def _worker_loop(self):
        """Worker thread main loop."""
        self.logger.info("Worker thread started")
        
        while self.running:
            try:
                # Check schedule
                schedule.run_pending()
                
                # Process tasks from queue
                if not self.task_queue.empty():
                    # Get next task (block with timeout)
                    try:
                        priority, task = self.task_queue.get(timeout=1)
                        
                        # Check if task is scheduled for future
                        if task.scheduled_for and task.scheduled_for > datetime.now():
                            # Requeue for later
                            self.task_queue.put((priority, task))
                            time.sleep(0.1)
                            continue
                        
                        # Execute task
                        self._execute_agent_task(task)
                        
                        # Mark task as done
                        self.task_queue.task_done()
                        
                    except queue.Empty:
                        pass
                
                # Sleep briefly to prevent CPU spinning
                time.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"Error in worker loop: {e}")
                time.sleep(1)  # Sleep longer on error
    
    def start(self):
        """Start the orchestrator."""
        if self.running:
            self.logger.warning("Orchestrator is already running")
            return
        
        self.running = True
        
        # Start worker thread
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        
        self.logger.info("Agent Orchestrator started")
        
        # Schedule initial tasks for enabled agents
        self._schedule_initial_tasks()
    
    def _schedule_initial_tasks(self):
        """Schedule initial tasks for all enabled agents."""
        for agent_name, agent_config in self.agents.items():
            if agent_config['enabled'] and agent_config['schedule'] != 'manual':
                # Schedule immediate run for agents that haven't run today
                last_run = agent_config.get('last_run')
                if not last_run or (datetime.now() - last_run).days >= 1:
                    self.schedule_agent_task(
                        agent_name=agent_name,
                        task_type='initial_run',
                        priority=TaskPriority.HIGH
                    )
                    self.logger.info(f"Scheduled initial run for {agent_name}")
    
    def stop(self):
        """Stop the orchestrator."""
        if not self.running:
            self.logger.warning("Orchestrator is not running")
            return
        
        self.running = False
        
        # Wait for worker thread to finish
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
        
        # Save state
        self._save_state()
        
        self.logger.info("Agent Orchestrator stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current orchestrator status."""
        status = {
            'running': self.running,
            'agents': {},
            'queue_size': self.task_queue.qsize(),
            'active_tasks': len(self.active_tasks),
            'completed_tasks': len(self.completed_tasks),
            'timestamp': datetime.now().isoformat()
        }
        
        # Add agent status
        for agent_name, agent_config in self.agents.items():
            agent_status = {
                'enabled': agent_config['enabled'],
                'schedule': agent_config['schedule'],
                'last_run': agent_config['last_run'].isoformat() if agent_config['last_run'] else None,
                'next_run': agent_config['next_run'].isoformat() if agent_config['next_run'] else None,
                'metrics': asdict(self.agent_metrics.get(agent_name, AgentMetrics(agent_name=agent_name)))
            }
            
            # Convert datetime in metrics
            if agent_status['metrics']['last_execution']:
                agent_status['metrics']['last_execution'] = agent_status['metrics']['last_execution'].isoformat()
            
            status['agents'][agent_name] = agent_status
        
        return status
    
    def get_agent_tasks(self, agent_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent tasks for an agent."""
        tasks = []
        
        # Check active tasks
        for task in self.active_tasks.values():
            if task.agent_name == agent_name:
                tasks.append(asdict(task))
        
        # Check completed tasks (most recent first)
        for task in reversed(self.completed_tasks):
            if task.agent_name == agent_name:
                tasks.append(asdict(task))
                if len(tasks) >= limit * 2:  # Get more to filter
                    break
        
        # Convert datetime objects
        for task in tasks:
            for key, value in task.items():
                if isinstance(value, datetime):
                    task[key] = value.isoformat()
                elif isinstance(value, (TaskPriority, AgentStatus)):
                    task[key] = value.name if hasattr(value, 'name') else str(value)
        
        return tasks[:limit]
    
    def run_agent_immediately(self, agent_name: str, task_type: str = "run",
                             parameters: Optional[Dict[str, Any]] = None) -> str:
        """
        Run an agent immediately with high priority.
        
        Args:
            agent_name: Name of the agent to run
            task_type: Type of task to execute
            parameters: Task parameters
            
        Returns:
            Task ID
        """
        return self.schedule_agent_task(
            agent_name=agent_name,
            task_type=task_type,
            priority=TaskPriority.CRITICAL,
            parameters=parameters or {},
            scheduled_for=None  # Immediate
        )
    
    def generate_orchestrator_report(self) -> str:
        """Generate a comprehensive orchestrator report."""
        status = self.get_status()
        
        report = []
        report.append("=" * 80)
        report.append("AGENT ORCHESTRATOR - SYSTEM STATUS REPORT")
        report.append("=" * 80)
        report.append("")
        
        # System Status
        report.append("SYSTEM STATUS")
        report.append("-" * 40)
        report.append(f"Orchestrator Running: {'Yes' if status['running'] else 'No'}")
        report.append(f"Tasks in Queue: {status['queue_size']}")
        report.append(f"Active Tasks: {status['active_tasks']}")
        report.append(f"Completed Tasks: {status['completed_tasks']}")
        report.append(f"Report Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Agent Status
        report.append("AGENT STATUS")
        report.append("-" * 40)
        
        for agent_name, agent_status in status['agents'].items():
            enabled_icon = "✓" if agent_status['enabled'] else "✗"
            schedule = agent_status['schedule']
            
            last_run = "Never"
            if agent_status['last_run']:
                last_dt = datetime.fromisoformat(agent_status['last_run'])
                last_run = last_dt.strftime('%Y-%m-%d %H:%M')
            
            next_run = "N/A"
            if agent_status['next_run']:
                next_dt = datetime.fromisoformat(agent_status['next_run'])
                next_run = next_dt.strftime('%Y-%m-%d %H:%M')
            
            metrics = agent_status['metrics']
            success_rate = f"{metrics['success_rate'] * 100:.1f}%"
            
            report.append(f"{enabled_icon} {agent_name}")
            report.append(f"  Schedule: {schedule}")
            report.append(f"  Last Run: {last_run}")
            report.append(f"  Next Run: {next_run}")
            report.append(f"  Success Rate: {success_rate}")
            report.append(f"  Total Tasks: {metrics['total_tasks']}")
            report.append("")
        
        # Recent Activity
        report.append("RECENT ACTIVITY")
        report.append("-" * 40)
        
        # Get recent completed tasks
        recent_tasks = self.completed_tasks[-5:] if self.completed_tasks else []
        
        if recent_tasks:
            for task in reversed(recent_tasks):
                time_str = task.completed_at.strftime('%H:%M') if task.completed_at else "N/A"
                result_summary = "Success" if task.status == AgentStatus.COMPLETED else f"Error: {task.error}"
                
                report.append(f"{time_str} - {task.agent_name}: {task.task_type} ({result_summary})")
        else:
            report.append("No recent activity")
        
        report.append("")
        report.append("=" * 80)
        report.append("ACTIONS:")
        report.append("1. Check individual agent outputs in shared_data/")
        report.append("2. Review agent-specific reports for detailed insights")
        report.append("3. Use run_agent_immediately() for on-demand execution")
        report.append("=" * 80)
        
        return "\n".join(report)


def main():
    """Main function to run the Agent Orchestrator."""
    print("Career Revolution - Agent Orchestrator")
    print("=" * 60)
    
    orchestrator = AgentOrchestrator()
    
    # Start the orchestrator
    print("\nStarting Agent Orchestrator...")
    orchestrator.start()
    
    try:
        # Run for a while to process tasks
        print("\nOrchestrator running. Press Ctrl+C to stop.")
        print("\nInitial status:")
        status = orchestrator.get_status()
        print(f"  Agents: {len(status['agents'])}")
        print(f"  Queue size: {status['queue_size']}")
        
        # Generate and display initial report
        time.sleep(2)  # Wait for initial tasks to be scheduled
        report = orchestrator.generate_orchestrator_report()
        print("\n" + report[:1000] + "..." if len(report) > 1000 else report)
        
        # Keep running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\nStopping orchestrator...")
    
    finally:
        # Stop the orchestrator
        orchestrator.stop()
        
        # Final report
        report = orchestrator.generate_orchestrator_report()
        print("\nFinal Status Report:")
        print("-" * 40)
        print(report[:500] + "..." if len(report) > 500 else report)
        
        print("\nAgent Orchestrator stopped successfully!")


if __name__ == "__main__":
    main()