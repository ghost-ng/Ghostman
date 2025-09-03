#!/usr/bin/env python3
"""
Complete Validation Suite Orchestrator for the Modernized Styling System.

This script orchestrates all validation suites and generates a comprehensive
validation report for the styling system modernization:

1. Comprehensive Styling System Validation
2. Performance Benchmark Suite  
3. Integration Test Suite
4. Final validation report with recommendations

Author: Claude Code (Sonnet 4)
Date: 2025-08-31
"""

import sys
import os
import time
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ValidationOrchestrator")

class ValidationOrchestrator:
    """Orchestrates all validation suites for the styling system."""
    
    def __init__(self):
        self.base_path = Path(__file__).parent
        self.results = {}
        self.start_time = time.time()
        
        # Validation suite configurations
        self.validation_suites = [
            {
                "name": "Comprehensive System Validation",
                "script": "comprehensive_styling_validation.py",
                "description": "Tests all aspects of the modernized styling system",
                "weight": 0.4  # 40% of total score
            },
            {
                "name": "Performance Benchmarks",
                "script": "performance_benchmark_suite.py", 
                "description": "Validates 80% performance improvement claims",
                "weight": 0.35  # 35% of total score
            },
            {
                "name": "Integration Tests",
                "script": "integration_test_suite.py",
                "description": "Tests integration between all system components",
                "weight": 0.25  # 25% of total score
            }
        ]
    
    def run_complete_validation(self) -> Dict[str, Any]:
        """Run all validation suites and generate final report."""
        print("🚀 COMPLETE STYLING SYSTEM VALIDATION")
        print("=" * 70)
        print("Running comprehensive validation of the modernized styling system...")
        print(f"Validation started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        total_suites = len(self.validation_suites)
        completed_suites = 0
        
        # Run each validation suite
        for suite_config in self.validation_suites:
            suite_name = suite_config["name"]
            script_name = suite_config["script"]
            
            print(f"\n{'='*20} {suite_name} {'='*20}")
            print(f"Running {script_name}...")
            
            try:
                # Run the validation suite
                result = self._run_validation_suite(script_name)
                
                if result["success"]:
                    print(f"✅ {suite_name} completed successfully")
                    completed_suites += 1
                else:
                    print(f"❌ {suite_name} completed with issues")
                    completed_suites += 1  # Still count as completed
                
                self.results[suite_name] = {
                    "config": suite_config,
                    "result": result,
                    "completed": True
                }
                
            except Exception as e:
                print(f"💥 {suite_name} failed to run: {e}")
                self.results[suite_name] = {
                    "config": suite_config,
                    "result": {"success": False, "error": str(e)},
                    "completed": False
                }
        
        total_time = time.time() - self.start_time
        
        print(f"\n{'='*70}")
        print("🏁 ALL VALIDATION SUITES COMPLETED")
        print(f"Completed: {completed_suites}/{total_suites} suites")
        print(f"Total execution time: {total_time:.1f}s")
        
        # Generate comprehensive report
        final_report = self._generate_final_report(total_time)
        
        # Save comprehensive report
        report_path = self.base_path / "FINAL_VALIDATION_REPORT.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(final_report, f, indent=2)
        
        # Generate human-readable summary
        summary_path = self.base_path / "VALIDATION_SUMMARY.md"
        self._generate_markdown_summary(final_report, summary_path)
        
        # Display final results
        self._display_final_results(final_report)
        
        return final_report
    
    def _run_validation_suite(self, script_name: str) -> Dict[str, Any]:
        """Run a single validation suite."""
        script_path = self.base_path / script_name
        
        if not script_path.exists():
            return {
                "success": False,
                "error": f"Validation script not found: {script_path}",
                "execution_time": 0
            }
        
        try:
            start_time = time.time()
            
            # Run the Python script
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            execution_time = time.time() - start_time
            
            # Try to load the generated report
            report_data = None
            report_files = {
                "comprehensive_styling_validation.py": "styling_validation_report.json",
                "performance_benchmark_suite.py": "performance_benchmark_report.json", 
                "integration_test_suite.py": "integration_test_report.json"
            }
            
            if script_name in report_files:
                report_file = self.base_path / report_files[script_name]
                if report_file.exists():
                    try:
                        with open(report_file, 'r', encoding='utf-8') as f:
                            report_data = json.load(f)
                    except Exception as e:
                        logger.warning(f"Failed to load report data from {report_file}: {e}")
            
            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "execution_time": execution_time,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "report_data": report_data
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Validation suite timed out (>10 minutes)",
                "execution_time": 600
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to execute validation suite: {e}",
                "execution_time": 0
            }
    
    def _generate_final_report(self, total_time: float) -> Dict[str, Any]:
        """Generate comprehensive final validation report."""
        
        # Analyze results from each suite
        suite_scores = {}
        suite_summaries = {}
        overall_metrics = {}
        
        for suite_name, suite_result in self.results.items():
            config = suite_result["config"]
            result = suite_result["result"]
            weight = config["weight"]
            
            if result.get("success", False) and result.get("report_data"):
                report_data = result["report_data"]
                
                # Extract key metrics based on suite type
                if "Comprehensive" in suite_name:
                    score = self._extract_comprehensive_score(report_data)
                elif "Performance" in suite_name:
                    score = self._extract_performance_score(report_data)
                elif "Integration" in suite_name:
                    score = self._extract_integration_score(report_data)
                else:
                    score = 50  # Default middling score
                    
                suite_scores[suite_name] = {
                    "score": score,
                    "weight": weight,
                    "weighted_score": score * weight
                }
                
                suite_summaries[suite_name] = self._extract_suite_summary(suite_name, report_data)
            else:
                # Suite failed or no data
                suite_scores[suite_name] = {
                    "score": 0,
                    "weight": weight,
                    "weighted_score": 0
                }
                suite_summaries[suite_name] = {
                    "status": "Failed",
                    "message": result.get("error", "Suite did not complete successfully")
                }
        
        # Calculate overall score
        total_weighted_score = sum(s["weighted_score"] for s in suite_scores.values())
        overall_score = total_weighted_score  # Already weighted
        
        # Determine overall status
        if overall_score >= 90:
            overall_status = "Excellent - Modernization fully successful"
            status_emoji = "🎉"
        elif overall_score >= 80:
            overall_status = "Good - Modernization largely successful"
            status_emoji = "✅"
        elif overall_score >= 70:
            overall_status = "Acceptable - Modernization mostly successful"
            status_emoji = "⚠️"
        elif overall_score >= 60:
            overall_status = "Poor - Modernization partially successful"
            status_emoji = "❌"
        else:
            overall_status = "Failed - Modernization unsuccessful"
            status_emoji = "💥"
        
        # Extract key achievements and issues
        achievements = self._extract_achievements()
        critical_issues = self._extract_critical_issues()
        recommendations = self._extract_recommendations()
        
        # Performance validation
        performance_validation = self._validate_performance_claims()
        
        # Final assessment
        final_assessment = {
            "modernization_complete": overall_score >= 75,
            "performance_targets_met": performance_validation.get("targets_met", False),
            "production_ready": overall_score >= 80 and len(critical_issues) == 0,
            "recommended_actions": recommendations[:5]  # Top 5 recommendations
        }
        
        return {
            "validation_metadata": {
                "timestamp": datetime.now().isoformat(),
                "total_execution_time_seconds": total_time,
                "validation_suites_run": len(self.validation_suites),
                "validation_suites_completed": sum(1 for r in self.results.values() if r["completed"]),
                "validator_version": "1.0.0",
                "python_version": sys.version
            },
            "overall_assessment": {
                "overall_score": round(overall_score, 1),
                "overall_status": overall_status,
                "status_emoji": status_emoji,
                "modernization_complete": final_assessment["modernization_complete"],
                "performance_targets_met": final_assessment["performance_targets_met"],
                "production_ready": final_assessment["production_ready"]
            },
            "suite_results": {
                "suite_scores": suite_scores,
                "suite_summaries": suite_summaries
            },
            "key_findings": {
                "achievements": achievements,
                "critical_issues": critical_issues,
                "performance_validation": performance_validation
            },
            "recommendations": {
                "immediate_actions": recommendations[:3],
                "improvement_opportunities": recommendations[3:6],
                "long_term_enhancements": recommendations[6:9]
            },
            "detailed_suite_data": {
                suite_name: result["result"].get("report_data", {})
                for suite_name, result in self.results.items()
                if result["result"].get("report_data")
            }
        }
    
    def _extract_comprehensive_score(self, report_data: Dict) -> float:
        """Extract score from comprehensive validation report."""
        try:
            summary = report_data.get("summary", {})
            success_rate = summary.get("success_rate_percent", 0)
            return min(100, success_rate)
        except:
            return 0
    
    def _extract_performance_score(self, report_data: Dict) -> float:
        """Extract score from performance benchmark report."""
        try:
            overall = report_data.get("overall_assessment", {})
            performance_score = overall.get("performance_score_percent", 0)
            
            improvement = report_data.get("improvement_validation", {})
            improvement_score = improvement.get("improvement_score_percent", 0)
            
            # Combine both scores with emphasis on improvement validation
            combined_score = (performance_score * 0.4) + (improvement_score * 0.6)
            return min(100, combined_score)
        except:
            return 0
    
    def _extract_integration_score(self, report_data: Dict) -> float:
        """Extract score from integration test report."""
        try:
            summary = report_data.get("summary", {})
            success_rate = summary.get("success_rate_percent", 0)
            
            coverage = report_data.get("integration_coverage", {})
            integration_coverage = coverage.get("integration_coverage_percent", 0)
            
            # Combine success rate and integration coverage
            combined_score = (success_rate * 0.7) + (integration_coverage * 0.3)
            return min(100, combined_score)
        except:
            return 0
    
    def _extract_suite_summary(self, suite_name: str, report_data: Dict) -> Dict[str, Any]:
        """Extract summary information from suite report."""
        try:
            if "Comprehensive" in suite_name:
                summary = report_data.get("summary", {})
                return {
                    "status": "Passed" if summary.get("success_rate_percent", 0) >= 80 else "Issues Found",
                    "tests_run": summary.get("total_tests", 0),
                    "tests_passed": summary.get("passed_tests", 0),
                    "success_rate": f"{summary.get('success_rate_percent', 0):.1f}%"
                }
            elif "Performance" in suite_name:
                assessment = report_data.get("overall_assessment", {})
                return {
                    "status": assessment.get("system_rating", "Unknown"),
                    "improvement_score": f"{report_data.get('improvement_validation', {}).get('improvement_score_percent', 0):.1f}%",
                    "performance_score": f"{assessment.get('performance_score_percent', 0):.1f}%"
                }
            elif "Integration" in suite_name:
                summary = report_data.get("summary", {})
                coverage = report_data.get("integration_coverage", {})
                return {
                    "status": summary.get("overall_status", "Unknown"),
                    "integration_coverage": f"{coverage.get('integration_coverage_percent', 0):.1f}%",
                    "tests_passed": summary.get("passed_tests", 0)
                }
            else:
                return {"status": "Unknown", "message": "Unable to parse suite results"}
        except Exception as e:
            return {"status": "Error", "message": f"Failed to parse results: {e}"}
    
    def _extract_achievements(self) -> List[str]:
        """Extract key achievements from all validation results."""
        achievements = []
        
        for suite_name, suite_result in self.results.items():
            result = suite_result["result"]
            
            if result.get("success") and result.get("report_data"):
                report_data = result["report_data"]
                
                if "Comprehensive" in suite_name:
                    summary = report_data.get("summary", {})
                    if summary.get("success_rate_percent", 0) >= 95:
                        achievements.append("✅ All styling system components working perfectly")
                    elif summary.get("success_rate_percent", 0) >= 85:
                        achievements.append("✅ Styling system architecture is solid")
                
                elif "Performance" in suite_name:
                    improvement = report_data.get("improvement_validation", {})
                    if improvement.get("improvement_score_percent", 0) >= 75:
                        achievements.append("🚀 Performance improvement targets exceeded")
                    
                    performance = report_data.get("performance_analysis", {})
                    if "theme_switching" in performance:
                        theme_data = performance["theme_switching"]
                        if theme_data.get("meets_target", False):
                            achievements.append(f"⚡ Theme switching optimized: {theme_data.get('avg_time_ms', 0):.1f}ms")
                
                elif "Integration" in suite_name:
                    coverage = report_data.get("integration_coverage", {})
                    if coverage.get("integration_coverage_percent", 0) >= 80:
                        achievements.append("🔗 Strong integration between all system components")
        
        # Add general achievements based on overall progress
        if len([r for r in self.results.values() if r["completed"]]) == len(self.validation_suites):
            achievements.append("📋 All validation suites completed successfully")
        
        return achievements[:8]  # Top 8 achievements
    
    def _extract_critical_issues(self) -> List[str]:
        """Extract critical issues from all validation results."""
        issues = []
        
        for suite_name, suite_result in self.results.items():
            result = suite_result["result"]
            
            if not result.get("success"):
                issues.append(f"💥 {suite_name} failed to complete")
                continue
            
            if result.get("report_data"):
                report_data = result["report_data"]
                
                if "Comprehensive" in suite_name:
                    summary = report_data.get("summary", {})
                    if summary.get("success_rate_percent", 0) < 70:
                        issues.append("❌ Major styling system functionality issues detected")
                    
                    # Check for specific critical issues
                    modernization = report_data.get("modernization_metrics", {})
                    if modernization.get("hardcoded_colors", 0) > 0:
                        issues.append(f"🎨 {modernization['hardcoded_colors']} hardcoded colors still remain")
                
                elif "Performance" in suite_name:
                    improvement = report_data.get("improvement_validation", {})
                    if improvement.get("improvement_score_percent", 0) < 50:
                        issues.append("🐌 Performance improvement targets not met")
                    
                    performance = report_data.get("performance_analysis", {})
                    if "theme_switching" in performance:
                        theme_data = performance["theme_switching"]
                        if not theme_data.get("meets_target", True):
                            issues.append(f"⏱️  Theme switching too slow: {theme_data.get('avg_time_ms', 0):.1f}ms")
                
                elif "Integration" in suite_name:
                    summary = report_data.get("summary", {})
                    if summary.get("success_rate_percent", 0) < 60:
                        issues.append("🔌 Poor integration between system components")
        
        return issues[:5]  # Top 5 critical issues
    
    def _extract_recommendations(self) -> List[str]:
        """Extract recommendations from all validation results.""" 
        recommendations = []
        
        for suite_name, suite_result in self.results.items():
            result = suite_result["result"]
            
            if result.get("report_data"):
                report_data = result["report_data"]
                
                # Extract recommendations from each suite's report
                suite_recommendations = report_data.get("recommendations", [])
                if isinstance(suite_recommendations, list):
                    recommendations.extend(suite_recommendations[:3])  # Top 3 from each suite
                elif isinstance(suite_recommendations, dict):
                    # Handle nested recommendation structure
                    for category, recs in suite_recommendations.items():
                        if isinstance(recs, list):
                            recommendations.extend(recs[:2])  # Top 2 from each category
        
        # Add general recommendations
        critical_issues = self._extract_critical_issues()
        if len(critical_issues) > 0:
            recommendations.append("Address critical issues before production deployment")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_recommendations = []
        for rec in recommendations:
            if rec not in seen:
                seen.add(rec)
                unique_recommendations.append(rec)
        
        return unique_recommendations[:10]  # Top 10 recommendations
    
    def _validate_performance_claims(self) -> Dict[str, Any]:
        """Validate the 80% performance improvement claims."""
        performance_validation = {
            "targets_met": False,
            "improvement_percentage": 0,
            "specific_metrics": {}
        }
        
        # Look for performance benchmark results
        for suite_name, suite_result in self.results.items():
            if "Performance" in suite_name and suite_result["result"].get("report_data"):
                report_data = suite_result["result"]["report_data"]
                
                improvement = report_data.get("improvement_validation", {})
                performance_validation["targets_met"] = improvement.get("improvement_score_percent", 0) >= 75
                performance_validation["improvement_percentage"] = improvement.get("improvement_score_percent", 0)
                
                # Extract specific metrics
                performance_analysis = report_data.get("performance_analysis", {})
                
                if "theme_switching" in performance_analysis:
                    theme_data = performance_analysis["theme_switching"]
                    performance_validation["specific_metrics"]["theme_switching_ms"] = theme_data.get("avg_time_ms", 0)
                    performance_validation["specific_metrics"]["theme_switching_target_met"] = theme_data.get("meets_target", False)
                
                if "cache_efficiency" in performance_analysis:
                    cache_data = performance_analysis["cache_efficiency"]
                    performance_validation["specific_metrics"]["cache_hit_rate"] = cache_data.get("hit_rate_percent", 0)
                    performance_validation["specific_metrics"]["cache_target_met"] = cache_data.get("meets_target", False)
                
                break
        
        return performance_validation
    
    def _generate_markdown_summary(self, report: Dict[str, Any], output_path: Path):
        """Generate human-readable markdown summary."""
        
        overall = report["overall_assessment"]
        suites = report["suite_results"]
        findings = report["key_findings"]
        recs = report["recommendations"]
        
        markdown_content = f"""# Styling System Modernization Validation Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Execution Time:** {report['validation_metadata']['total_execution_time_seconds']:.1f} seconds

## {overall['status_emoji']} Overall Assessment

**Overall Score:** {overall['overall_score']}/100  
**Status:** {overall['overall_status']}

- **Modernization Complete:** {'✅ Yes' if overall['modernization_complete'] else '❌ No'}
- **Performance Targets Met:** {'✅ Yes' if overall['performance_targets_met'] else '❌ No'}  
- **Production Ready:** {'✅ Yes' if overall['production_ready'] else '❌ No'}

## 📊 Validation Suite Results

"""
        
        for suite_name, score_data in suites["suite_scores"].items():
            summary = suites["suite_summaries"].get(suite_name, {})
            markdown_content += f"""### {suite_name}
- **Score:** {score_data['score']:.1f}/100 (Weight: {score_data['weight']*100:.0f}%)
- **Status:** {summary.get('status', 'Unknown')}
"""
            
            # Add suite-specific details
            if 'success_rate' in summary:
                markdown_content += f"- **Success Rate:** {summary['success_rate']}\n"
            if 'improvement_score' in summary:
                markdown_content += f"- **Improvement Score:** {summary['improvement_score']}\n"
            if 'integration_coverage' in summary:
                markdown_content += f"- **Integration Coverage:** {summary['integration_coverage']}\n"
            
            markdown_content += "\n"
        
        # Key Findings
        markdown_content += "## 🎯 Key Findings\n\n"
        
        if findings["achievements"]:
            markdown_content += "### Achievements\n"
            for achievement in findings["achievements"]:
                markdown_content += f"- {achievement}\n"
            markdown_content += "\n"
        
        if findings["critical_issues"]:
            markdown_content += "### Critical Issues\n"
            for issue in findings["critical_issues"]:
                markdown_content += f"- {issue}\n"
            markdown_content += "\n"
        
        # Performance Validation
        perf_validation = findings["performance_validation"]
        markdown_content += f"""### Performance Validation
- **Improvement Targets Met:** {'✅ Yes' if perf_validation['targets_met'] else '❌ No'}
- **Improvement Score:** {perf_validation['improvement_percentage']:.1f}%

"""
        
        # Recommendations
        markdown_content += "## 📋 Recommendations\n\n"
        
        if recs["immediate_actions"]:
            markdown_content += "### Immediate Actions\n"
            for rec in recs["immediate_actions"]:
                markdown_content += f"1. {rec}\n"
            markdown_content += "\n"
        
        if recs["improvement_opportunities"]:
            markdown_content += "### Improvement Opportunities\n" 
            for rec in recs["improvement_opportunities"]:
                markdown_content += f"- {rec}\n"
            markdown_content += "\n"
        
        if recs["long_term_enhancements"]:
            markdown_content += "### Long-term Enhancements\n"
            for rec in recs["long_term_enhancements"]:
                markdown_content += f"- {rec}\n"
            markdown_content += "\n"
        
        # Footer
        markdown_content += f"""
---
*Report generated by Styling System Validation Suite v{report['validation_metadata']['validator_version']}*
*Validation completed in {report['validation_metadata']['total_execution_time_seconds']:.1f} seconds*
"""
        
        # Write markdown file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
    
    def _display_final_results(self, report: Dict[str, Any]):
        """Display final validation results to console."""
        
        overall = report["overall_assessment"]
        findings = report["key_findings"]
        
        print(f"\n🎯 FINAL VALIDATION RESULTS")
        print("=" * 70)
        print(f"{overall['status_emoji']} Overall Score: {overall['overall_score']}/100")
        print(f"Status: {overall['overall_status']}")
        print()
        
        print("Key Metrics:")
        print(f"  • Modernization Complete: {'✅' if overall['modernization_complete'] else '❌'}")
        print(f"  • Performance Targets Met: {'✅' if overall['performance_targets_met'] else '❌'}")
        print(f"  • Production Ready: {'✅' if overall['production_ready'] else '❌'}")
        print()
        
        if findings["achievements"]:
            print("🏆 Key Achievements:")
            for achievement in findings["achievements"][:5]:
                print(f"  {achievement}")
            print()
        
        if findings["critical_issues"]:
            print("⚠️  Critical Issues:")
            for issue in findings["critical_issues"][:3]:
                print(f"  {issue}")
            print()
        
        # Performance summary
        perf_validation = findings["performance_validation"]
        print("⚡ Performance Validation:")
        print(f"  • Improvement Score: {perf_validation['improvement_percentage']:.1f}%")
        print(f"  • Targets Met: {'✅' if perf_validation['targets_met'] else '❌'}")
        
        if "theme_switching_ms" in perf_validation["specific_metrics"]:
            theme_time = perf_validation["specific_metrics"]["theme_switching_ms"]
            print(f"  • Theme Switching: {theme_time:.1f}ms")
        
        print()
        print("📋 Reports Generated:")
        print(f"  • Comprehensive JSON: {self.base_path / 'FINAL_VALIDATION_REPORT.json'}")
        print(f"  • Human-readable Summary: {self.base_path / 'VALIDATION_SUMMARY.md'}")
        print()


def main():
    """Main entry point for complete validation."""
    
    print("🧪 COMPLETE STYLING SYSTEM MODERNIZATION VALIDATION")
    print("This comprehensive validation suite will test all aspects")
    print("of the modernized styling system and generate a final report.")
    print()
    
    orchestrator = ValidationOrchestrator()
    
    try:
        final_report = orchestrator.run_complete_validation()
        
        overall_score = final_report["overall_assessment"]["overall_score"]
        production_ready = final_report["overall_assessment"]["production_ready"]
        
        # Return appropriate exit code
        if production_ready and overall_score >= 85:
            print("🎉 Styling system modernization is complete and production-ready!")
            return 0
        elif overall_score >= 75:
            print("✅ Styling system modernization is largely successful with minor issues.")
            return 0
        elif overall_score >= 60:
            print("⚠️  Styling system modernization has significant issues that need addressing.")
            return 1
        else:
            print("❌ Styling system modernization validation failed.")
            return 2
            
    except KeyboardInterrupt:
        print("\n❌ Validation interrupted by user")
        return 3
    except Exception as e:
        print(f"\n💥 Validation orchestrator failed: {e}")
        import traceback
        traceback.print_exc()
        return 4


if __name__ == "__main__":
    sys.exit(main())