        return {
            'connections_analyzed': len(connections),
            'high_value_connections': len(high_value),
            'outreach_messages': len(messages),
            'report_file': report_file,
            'report_preview': report[:500] + "..." if len(report) > 500 else report
        }


def main():
    """Main function to run the Network Agent."""
    print("Career Revolution - Network Agent")
    print("=" * 60)
    
    agent = NetworkAgent()
    
    # Run complete workflow
    results = agent.run_complete_workflow()
    
    print(f"\nResults:")
    print(f"  Connections analyzed: {results['connections_analyzed']}")
    print(f"  High-value connections: {results['high_value_connections']}")
    print(f"  Outreach messages: {results['outreach_messages']}")
    print(f"  Report file: {results['report_file']}")
    
    # Print report preview
    print("\nReport Preview:")
    print("-" * 40)
    print(results['report_preview'])
    
    print("\nNetwork Agent completed successfully!")


if __name__ == "__main__":
    main()