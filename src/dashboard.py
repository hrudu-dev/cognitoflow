#!/usr/bin/env python3
"""
CognitoFlow Dashboard

Web-based dashboard for monitoring and managing CognitoFlow AI policy engine.
Provides real-time insights into policy enforcement, compliance status, and system health.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any
import boto3

# Import CognitoFlow modules
from policy_engine import CognitoFlowPolicyEngine
from ai_sdlc import CognitoFlowAISDLC

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CognitoFlowDashboard:
    """
    Dashboard for CognitoFlow monitoring and management
    """
    
    def __init__(self, policy_engine: CognitoFlowPolicyEngine, ai_sdlc: CognitoFlowAISDLC):
        self.policy_engine = policy_engine
        self.ai_sdlc = ai_sdlc
    
    def get_compliance_metrics(self) -> Dict[str, Any]:
        """Get compliance metrics for dashboard"""
        try:
            dashboard_data = self.policy_engine.get_compliance_dashboard()
            
            # Calculate additional metrics
            summary = dashboard_data.get('summary', {})
            compliance_rate = summary.get('compliance_rate', 0)
            
            # Compliance status
            if compliance_rate >= 95:
                compliance_status = 'excellent'
            elif compliance_rate >= 85:
                compliance_status = 'good'
            elif compliance_rate >= 70:
                compliance_status = 'warning'
            else:
                compliance_status = 'critical'
            
            return {
                'compliance_rate': compliance_rate,
                'compliance_status': compliance_status,
                'total_policies': summary.get('total_policies', 0),
                'total_enforcements': summary.get('total_enforcements', 0),
                'successful_enforcements': summary.get('successful_enforcements', 0),
                'failed_enforcements': summary.get('failed_enforcements', 0),
                'policy_statistics': dashboard_data.get('policy_statistics', {}),
                'action_statistics': dashboard_data.get('action_statistics', {}),
                'recent_events': dashboard_data.get('recent_events', [])
            }
        
        except Exception as e:
            logger.error(f"Error getting compliance metrics: {e}")
            return {}
    
    def get_ai_sdlc_metrics(self) -> Dict[str, Any]:
        """Get AI SDLC metrics for dashboard"""
        try:
            # Get project statistics
            total_projects = len(self.ai_sdlc.projects)
            total_experiments = len(self.ai_sdlc.experiments)
            total_deployments = len(self.ai_sdlc.deployments)
            
            # Calculate success rates
            successful_experiments = len([exp for exp in self.ai_sdlc.experiments.values() 
                                        if exp.deployment_ready])
            experiment_success_rate = (successful_experiments / total_experiments * 100) if total_experiments > 0 else 0
            
            # Get compliance scores
            compliance_scores = [exp.compliance_score for exp in self.ai_sdlc.experiments.values()]
            avg_compliance_score = sum(compliance_scores) / len(compliance_scores) if compliance_scores else 0
            
            return {
                'total_projects': total_projects,
                'total_experiments': total_experiments,
                'total_deployments': total_deployments,
                'experiment_success_rate': experiment_success_rate,
                'avg_compliance_score': avg_compliance_score,
                'active_deployments': total_deployments,
                'model_performance': self._get_model_performance_summary()
            }
        
        except Exception as e:
            logger.error(f"Error getting AI SDLC metrics: {e}")
            return {}
    
    def _get_model_performance_summary(self) -> Dict[str, Any]:
        """Get model performance summary"""
        try:
            performance_data = []
            
            for deployment_id in self.ai_sdlc.deployments.keys():
                monitoring_data = self.ai_sdlc.monitor_model_performance(deployment_id)
                performance_data.append({
                    'deployment_id': deployment_id,
                    'latency_p95': monitoring_data['performance_metrics']['latency_p95'],
                    'bias_score': monitoring_data['compliance_metrics']['bias_score'],
                    'drift_score': monitoring_data['compliance_metrics']['drift_score'],
                    'alerts': len(monitoring_data['alerts'])
                })
            
            return {
                'deployments': performance_data,
                'avg_latency': sum(d['latency_p95'] for d in performance_data) / len(performance_data) if performance_data else 0,
                'avg_bias_score': sum(d['bias_score'] for d in performance_data) / len(performance_data) if performance_data else 0,
                'total_alerts': sum(d['alerts'] for d in performance_data)
            }
        
        except Exception as e:
            logger.error(f"Error getting model performance: {e}")
            return {}
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get system health metrics"""
        try:
            # Simulate system health checks
            return {
                'policy_engine_status': 'healthy',
                'ai_sdlc_status': 'healthy',
                'database_status': 'healthy',
                'aws_services_status': 'healthy',
                'last_health_check': datetime.utcnow().isoformat(),
                'uptime_percentage': 99.9,
                'response_time_ms': 45.2,
                'error_rate_percentage': 0.1
            }
        
        except Exception as e:
            logger.error(f"Error getting system health: {e}")
            return {}
    
    def get_dashboard_summary(self) -> Dict[str, Any]:
        """Get complete dashboard summary"""
        try:
            compliance_metrics = self.get_compliance_metrics()
            ai_sdlc_metrics = self.get_ai_sdlc_metrics()
            system_health = self.get_system_health()
            
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'compliance': compliance_metrics,
                'ai_sdlc': ai_sdlc_metrics,
                'system_health': system_health,
                'alerts': self._get_active_alerts(),
                'recommendations': self._get_recommendations()
            }
        
        except Exception as e:
            logger.error(f"Error getting dashboard summary: {e}")
            return {}
    
    def _get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get active system alerts"""
        alerts = []
        
        try:
            # Check compliance rate
            compliance_metrics = self.get_compliance_metrics()
            compliance_rate = compliance_metrics.get('compliance_rate', 0)
            
            if compliance_rate < 95:
                alerts.append({
                    'type': 'compliance',
                    'severity': 'warning' if compliance_rate >= 85 else 'critical',
                    'message': f'Compliance rate is {compliance_rate:.1f}%',
                    'timestamp': datetime.utcnow().isoformat()
                })
            
            # Check model performance
            ai_metrics = self.get_ai_sdlc_metrics()
            model_performance = ai_metrics.get('model_performance', {})
            total_alerts = model_performance.get('total_alerts', 0)
            
            if total_alerts > 0:
                alerts.append({
                    'type': 'performance',
                    'severity': 'warning',
                    'message': f'{total_alerts} model performance alerts active',
                    'timestamp': datetime.utcnow().isoformat()
                })
            
            # Check system health
            system_health = self.get_system_health()
            uptime = system_health.get('uptime_percentage', 100)
            
            if uptime < 99.5:
                alerts.append({
                    'type': 'system',
                    'severity': 'critical',
                    'message': f'System uptime is {uptime:.1f}%',
                    'timestamp': datetime.utcnow().isoformat()
                })
        
        except Exception as e:
            logger.error(f"Error getting alerts: {e}")
        
        return alerts
    
    def _get_recommendations(self) -> List[Dict[str, Any]]:
        """Get system recommendations"""
        recommendations = []
        
        try:
            compliance_metrics = self.get_compliance_metrics()
            ai_metrics = self.get_ai_sdlc_metrics()
            
            # Compliance recommendations
            if compliance_metrics.get('compliance_rate', 0) < 95:
                recommendations.append({
                    'category': 'compliance',
                    'priority': 'high',
                    'title': 'Improve Compliance Rate',
                    'description': 'Review failed policy enforcements and update rules',
                    'action': 'Review audit logs and policy configurations'
                })
            
            # AI SDLC recommendations
            if ai_metrics.get('avg_compliance_score', 0) < 0.9:
                recommendations.append({
                    'category': 'ai_sdlc',
                    'priority': 'medium',
                    'title': 'Enhance Model Compliance',
                    'description': 'Improve model compliance scores through better training data',
                    'action': 'Review data quality and bias detection settings'
                })
            
            # Performance recommendations
            model_performance = ai_metrics.get('model_performance', {})
            if model_performance.get('avg_latency', 0) > 100:
                recommendations.append({
                    'category': 'performance',
                    'priority': 'medium',
                    'title': 'Optimize Model Latency',
                    'description': 'Model response times are above optimal threshold',
                    'action': 'Consider upgrading instance types or optimizing models'
                })
        
        except Exception as e:
            logger.error(f"Error getting recommendations: {e}")
        
        return recommendations
    
    def export_compliance_report(self, format_type: str = 'json') -> Dict[str, Any]:
        """Export compliance report"""
        try:
            report_data = {
                'report_id': f"compliance_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                'generated_at': datetime.utcnow().isoformat(),
                'report_period': {
                    'start_date': (datetime.utcnow() - timedelta(days=30)).isoformat(),
                    'end_date': datetime.utcnow().isoformat()
                },
                'executive_summary': {
                    'overall_compliance_rate': self.get_compliance_metrics().get('compliance_rate', 0),
                    'total_policies': len(self.policy_engine.policies),
                    'total_enforcements': self.get_compliance_metrics().get('total_enforcements', 0),
                    'critical_issues': len([a for a in self._get_active_alerts() if a.get('severity') == 'critical'])
                },
                'detailed_metrics': self.get_compliance_metrics(),
                'policy_performance': self._get_policy_performance_details(),
                'recommendations': self._get_recommendations(),
                'audit_summary': self._get_audit_summary()
            }
            
            return report_data
        
        except Exception as e:
            logger.error(f"Error exporting compliance report: {e}")
            return {}
    
    def _get_policy_performance_details(self) -> Dict[str, Any]:
        """Get detailed policy performance metrics"""
        try:
            policy_details = {}
            
            for policy_id, policy in self.policy_engine.policies.items():
                status = self.policy_engine.get_policy_status(policy_id)
                policy_details[policy_id] = {
                    'name': policy.name,
                    'compliance_frameworks': policy.compliance_frameworks,
                    'total_enforcements': status.get('total_enforcements', 0),
                    'success_rate': (status.get('successful_enforcements', 0) / 
                                   max(status.get('total_enforcements', 1), 1) * 100),
                    'last_enforcement': status.get('last_enforcement')
                }
            
            return policy_details
        
        except Exception as e:
            logger.error(f"Error getting policy performance details: {e}")
            return {}
    
    def _get_audit_summary(self) -> Dict[str, Any]:
        """Get audit trail summary"""
        try:
            with open(self.policy_engine.audit_log_path, 'r') as f:
                audit_log = json.load(f)
            
            # Calculate audit metrics
            total_events = len(audit_log)
            recent_events = [e for e in audit_log 
                           if datetime.fromisoformat(e['timestamp'].replace('Z', '+00:00')) > 
                           datetime.utcnow().replace(tzinfo=None) - timedelta(days=7)]
            
            action_counts = {}
            for event in audit_log:
                action = event.get('action_taken', 'unknown')
                action_counts[action] = action_counts.get(action, 0) + 1
            
            return {
                'total_audit_events': total_events,
                'recent_events_count': len(recent_events),
                'action_distribution': action_counts,
                'compliance_violations': len([e for e in audit_log if not e.get('success', True)]),
                'most_active_policy': max(action_counts.keys(), key=action_counts.get) if action_counts else None
            }
        
        except Exception as e:
            logger.error(f"Error getting audit summary: {e}")
            return {}

# Example usage
if __name__ == "__main__":
    # Initialize components
    policy_engine = CognitoFlowPolicyEngine(
        cognito_user_pool_id="us-east-1_example123",
        region="us-east-1"
    )
    
    ai_sdlc = CognitoFlowAISDLC(region="us-east-1")
    
    # Create dashboard
    dashboard = CognitoFlowDashboard(policy_engine, ai_sdlc)
    
    # Get dashboard summary
    summary = dashboard.get_dashboard_summary()
    print("CognitoFlow Dashboard Summary:")
    print(f"Compliance Rate: {summary['compliance']['compliance_rate']:.1f}%")
    print(f"Total Policies: {summary['compliance']['total_policies']}")
    print(f"Active Alerts: {len(summary['alerts'])}")
    print(f"System Health: {summary['system_health']['policy_engine_status']}")
    
    # Export compliance report
    report = dashboard.export_compliance_report()
    print(f"\nCompliance Report Generated: {report['report_id']}")
    print(f"Overall Compliance: {report['executive_summary']['overall_compliance_rate']:.1f}%")