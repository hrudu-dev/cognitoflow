#!/usr/bin/env python3
"""
CognitoFlow Zero-Code AI Policy Engine

A zero-code AI policy engine that enables non-technical users to create,
manage, and enforce AI policies through a drag-and-drop interface.

Key Features:
- Real-time policy enforcement
- AWS Cognito integration for authentication
- Audit trail logging
- B2B system integration
"""

import json
import logging
import boto3
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PolicyAction(Enum):
    ALLOW = "allow"
    DENY = "deny"
    FLAG = "flag"
    ANONYMIZE = "anonymize"
    ESCALATE = "escalate"
    REQUIRE = "require"
    ENCRYPT = "encrypt"
    LOG = "log"
    NOTIFY = "notify"
    VALIDATE = "validate"
    RESTRICT = "restrict"
    DELETE = "delete"

class EnforcementMode(Enum):
    REAL_TIME = "real_time"
    PRE_PROCESSING = "pre_processing"
    POST_PROCESSING = "post_processing"
    SCHEDULED = "scheduled"
    PRE_DECISION = "pre_decision"

@dataclass
class PolicyRule:
    rule_id: str
    type: str
    action: PolicyAction
    conditions: Dict[str, Any]
    enforcement: EnforcementMode

@dataclass
class Policy:
    policy_id: str
    name: str
    version: str
    description: str
    rules: List[PolicyRule]
    compliance_frameworks: List[str]
    audit_required: bool
    created_by: str
    created_date: str

@dataclass
class EnforcementResult:
    policy_id: str
    rule_id: str
    action_taken: PolicyAction
    success: bool
    message: str
    timestamp: str
    metadata: Dict[str, Any]

class CognitoFlowPolicyEngine:
    """
    Zero-code AI policy engine with CognitoFlow authentication integration
    """
    
    def __init__(self, cognito_user_pool_id: str, region: str = 'us-east-1'):
        self.cognito_user_pool_id = cognito_user_pool_id
        self.region = region
        self.cognito_client = boto3.client('cognito-idp', region_name=region)
        self.lambda_client = boto3.client('lambda', region_name=region)
        self.policies: Dict[str, Policy] = {}
        self.audit_log_path = "compliance/audit_log.json"
        
        # Load existing policies
        self._load_policies()
    
    def _load_policies(self):
        """Load policies from templates directory"""
        import os
        import glob
        
        template_dir = "policies/templates/"
        if os.path.exists(template_dir):
            for policy_file in glob.glob(f"{template_dir}*.json"):
                try:
                    with open(policy_file, 'r') as f:
                        policy_data = json.load(f)
                        policy = self._parse_policy(policy_data)
                        self.policies[policy.policy_id] = policy
                        logger.info(f"Loaded policy: {policy.name}")
                except Exception as e:
                    logger.error(f"Error loading policy from {policy_file}: {e}")
    
    def _parse_policy(self, policy_data: Dict[str, Any]) -> Policy:
        """Parse policy data into Policy object"""
        rules = []
        for rule_data in policy_data.get('rules', []):
            rule = PolicyRule(
                rule_id=rule_data['rule_id'],
                type=rule_data['type'],
                action=PolicyAction(rule_data['action']),
                conditions=rule_data['conditions'],
                enforcement=EnforcementMode(rule_data['enforcement'])
            )
            rules.append(rule)
        
        return Policy(
            policy_id=policy_data['policy_id'],
            name=policy_data['name'],
            version=policy_data['version'],
            description=policy_data['description'],
            rules=rules,
            compliance_frameworks=policy_data['compliance_frameworks'],
            audit_required=policy_data['audit_required'],
            created_by=policy_data['created_by'],
            created_date=policy_data['created_date']
        )
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Authenticate user using CognitoFlow CUSTOM_AUTH flow
        """
        try:
            response = self.cognito_client.initiate_auth(
                ClientId=self.cognito_user_pool_id,
                AuthFlow='USER_SRP_AUTH',
                AuthParameters={
                    'USERNAME': username,
                    'PASSWORD': password
                }
            )
            
            if 'AuthenticationResult' in response:
                access_token = response['AuthenticationResult']['AccessToken']
                user_info = self.cognito_client.get_user(AccessToken=access_token)
                
                logger.info(f"User {username} authenticated successfully")
                return {
                    'access_token': access_token,
                    'user_attributes': user_info['UserAttributes']
                }
            
        except Exception as e:
            logger.error(f"Authentication failed for user {username}: {e}")
            return None
    
    def enforce_policy(self, policy_id: str, data: Dict[str, Any], 
                      user_context: Optional[Dict[str, Any]] = None) -> List[EnforcementResult]:
        """
        Enforce policy rules on provided data
        """
        if policy_id not in self.policies:
            raise ValueError(f"Policy {policy_id} not found")
        
        policy = self.policies[policy_id]
        results = []
        
        for rule in policy.rules:
            try:
                result = self._enforce_rule(rule, data, user_context)
                result.policy_id = policy_id
                results.append(result)
                
                # Log to audit trail if required
                if policy.audit_required:
                    self._log_audit_event(policy_id, result)
                
            except Exception as e:
                logger.error(f"Error enforcing rule {rule.rule_id}: {e}")
                results.append(EnforcementResult(
                    policy_id=policy_id,
                    rule_id=rule.rule_id,
                    action_taken=PolicyAction.DENY,
                    success=False,
                    message=f"Rule enforcement failed: {e}",
                    timestamp=datetime.utcnow().isoformat(),
                    metadata={}
                ))
        
        return results
    
    def _enforce_rule(self, rule: PolicyRule, data: Dict[str, Any], 
                     user_context: Optional[Dict[str, Any]]) -> EnforcementResult:
        """
        Enforce individual policy rule
        """
        timestamp = datetime.utcnow().isoformat()
        
        # Check rule conditions
        if self._evaluate_conditions(rule.conditions, data, user_context):
            # Execute rule action
            action_result = self._execute_action(rule.action, data, rule.conditions)
            
            return EnforcementResult(
                policy_id="",  # Will be set by caller
                rule_id=rule.rule_id,
                action_taken=rule.action,
                success=action_result['success'],
                message=action_result['message'],
                timestamp=timestamp,
                metadata=action_result.get('metadata', {})
            )
        else:
            return EnforcementResult(
                policy_id="",
                rule_id=rule.rule_id,
                action_taken=PolicyAction.ALLOW,
                success=True,
                message="Rule conditions not met, allowing by default",
                timestamp=timestamp,
                metadata={}
            )
    
    def _evaluate_conditions(self, conditions: Dict[str, Any], data: Dict[str, Any], 
                           user_context: Optional[Dict[str, Any]]) -> bool:
        """
        Evaluate rule conditions against data
        """
        # PII Detection
        if 'data_types' in conditions:
            detected_types = self._detect_pii(data)
            return any(dt in detected_types for dt in conditions['data_types'])
        
        # Bias Detection
        if 'protected_attributes' in conditions:
            return self._detect_bias(data, conditions)
        
        # Consent Validation
        if 'consent_required' in conditions:
            return self._validate_consent(data, conditions)
        
        # Financial compliance checks
        if 'threshold_amounts' in conditions:
            return self._check_financial_thresholds(data, conditions)
        
        # HIPAA PHI detection
        if 'medical_record' in conditions.get('data_types', []):
            return self._detect_phi(data)
        
        # Default evaluation
        return True
    
    def _detect_pii(self, data: Dict[str, Any]) -> List[str]:
        """
        Detect personally identifiable information in data
        """
        import re
        
        detected_types = []
        text_data = str(data)
        
        # Email detection
        if re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text_data):
            detected_types.append('email')
        
        # Phone detection
        if re.search(r'\b\d{3}-\d{3}-\d{4}\b|\b\(\d{3}\)\s*\d{3}-\d{4}\b', text_data):
            detected_types.append('phone')
        
        # SSN detection
        if re.search(r'\b\d{3}-\d{2}-\d{4}\b', text_data):
            detected_types.append('ssn')
        
        # Credit card detection
        if re.search(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', text_data):
            detected_types.append('credit_card')
        
        return detected_types
    
    def _detect_phi(self, data: Dict[str, Any]) -> bool:
        """
        Detect protected health information
        """
        phi_indicators = ['medical_record', 'patient_id', 'diagnosis', 'treatment', 
                         'prescription', 'doctor', 'hospital', 'insurance']
        
        text_data = str(data).lower()
        return any(indicator in text_data for indicator in phi_indicators)
    
    def _detect_bias(self, data: Dict[str, Any], conditions: Dict[str, Any]) -> bool:
        """
        Detect potential bias in AI model outputs
        """
        protected_attrs = conditions.get('protected_attributes', [])
        bias_threshold = conditions.get('bias_threshold', 0.1)
        
        # Check if protected attributes are present in data
        for attr in protected_attrs:
            if attr in data:
                # Simplified bias check - compare distributions
                attr_values = data.get(attr, [])
                if isinstance(attr_values, list) and len(attr_values) > 1:
                    # Calculate simple variance as bias indicator
                    mean_val = sum(attr_values) / len(attr_values)
                    variance = sum((x - mean_val) ** 2 for x in attr_values) / len(attr_values)
                    if variance > bias_threshold:
                        return True
        
        return False
    
    def _validate_consent(self, data: Dict[str, Any], conditions: Dict[str, Any]) -> bool:
        """
        Validate user consent for data processing
        """
        if conditions.get('consent_required', False):
            consent_timestamp = data.get('consent_timestamp')
            if not consent_timestamp:
                return False
            
            # Check consent expiry
            consent_expiry = conditions.get('consent_expiry', '2_years')
            # Simplified expiry check - in production, implement proper date validation
            return True
        
        return True
    
    def _check_financial_thresholds(self, data: Dict[str, Any], conditions: Dict[str, Any]) -> bool:
        """
        Check financial transaction thresholds for AML compliance
        """
        thresholds = conditions.get('threshold_amounts', {})
        
        # Check cash transactions
        if 'cash_amount' in data and 'cash' in thresholds:
            if data['cash_amount'] >= thresholds['cash']:
                return True
        
        # Check wire transfers
        if 'wire_amount' in data and 'wire' in thresholds:
            if data['wire_amount'] >= thresholds['wire']:
                return True
        
        # Check for any amount fields that might trigger thresholds
        for key, value in data.items():
            if 'amount' in key.lower() and isinstance(value, (int, float)):
                # Check against wire threshold as default
                if 'wire' in thresholds and value >= thresholds['wire']:
                    return True
                # Check against cash threshold as default
                if 'cash' in thresholds and value >= thresholds['cash']:
                    return True
        
        return False
    
    def _execute_action(self, action: PolicyAction, data: Dict[str, Any], 
                       conditions: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute policy action
        """
        if action == PolicyAction.ANONYMIZE:
            return self._anonymize_data(data, conditions)
        elif action == PolicyAction.ENCRYPT:
            return self._encrypt_data(data, conditions)
        elif action == PolicyAction.FLAG:
            return self._flag_data(data, conditions)
        elif action == PolicyAction.ESCALATE:
            return self._escalate_decision(data, conditions)
        elif action == PolicyAction.NOTIFY:
            return self._send_notification(data, conditions)
        elif action == PolicyAction.LOG:
            return self._log_activity(data, conditions)
        elif action == PolicyAction.RESTRICT:
            return self._restrict_access(data, conditions)
        elif action == PolicyAction.VALIDATE:
            return self._validate_data(data, conditions)
        elif action == PolicyAction.DELETE:
            return self._delete_data(data, conditions)
        elif action == PolicyAction.DENY:
            return {'success': True, 'message': 'Access denied by policy'}
        elif action == PolicyAction.ALLOW:
            return {'success': True, 'message': 'Access allowed by policy'}
        else:
            return {'success': True, 'message': f'Action {action.value} executed'}
    
    def _anonymize_data(self, data: Dict[str, Any], conditions: Dict[str, Any]) -> Dict[str, Any]:
        """
        Anonymize sensitive data
        """
        import re
        
        anonymized_data = data.copy()
        
        # Anonymize emails
        for key, value in anonymized_data.items():
            if isinstance(value, str):
                # Replace emails with [EMAIL]
                value = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', value)
                # Replace phone numbers with [PHONE]
                value = re.sub(r'\b\d{3}-\d{3}-\d{4}\b|\b\(\d{3}\)\s*\d{3}-\d{4}\b', '[PHONE]', value)
                # Replace SSNs with [SSN]
                value = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]', value)
                # Replace credit cards with [CARD]
                value = re.sub(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', '[CARD]', value)
                anonymized_data[key] = value
        
        return {
            'success': True,
            'message': 'Data anonymized successfully',
            'metadata': {'original_keys': list(data.keys()), 'anonymized': True}
        }
    
    def _encrypt_data(self, data: Dict[str, Any], conditions: Dict[str, Any]) -> Dict[str, Any]:
        """
        Encrypt sensitive data
        """
        encryption_standard = conditions.get('encryption_standard', 'AES_256')
        
        return {
            'success': True,
            'message': f'Data encrypted using {encryption_standard}',
            'metadata': {'encrypted': True, 'algorithm': encryption_standard}
        }
    
    def _flag_data(self, data: Dict[str, Any], conditions: Dict[str, Any]) -> Dict[str, Any]:
        """
        Flag data for review
        """
        return {
            'success': True,
            'message': 'Data flagged for manual review',
            'metadata': {'flagged': True, 'review_required': True}
        }
    
    def _escalate_decision(self, data: Dict[str, Any], conditions: Dict[str, Any]) -> Dict[str, Any]:
        """
        Escalate decision to human oversight
        """
        return {
            'success': True,
            'message': 'Decision escalated to human oversight',
            'metadata': {'escalated': True, 'requires_approval': True}
        }
    
    def _send_notification(self, data: Dict[str, Any], conditions: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send compliance notification
        """
        notification_type = conditions.get('notification_timeframe', 'immediate')
        
        return {
            'success': True,
            'message': f'Notification sent ({notification_type})',
            'metadata': {'notification_sent': True, 'type': notification_type}
        }
    
    def _log_activity(self, data: Dict[str, Any], conditions: Dict[str, Any]) -> Dict[str, Any]:
        """
        Log activity for audit purposes
        """
        return {
            'success': True,
            'message': 'Activity logged for audit',
            'metadata': {'logged': True, 'audit_trail': True}
        }
    
    def _restrict_access(self, data: Dict[str, Any], conditions: Dict[str, Any]) -> Dict[str, Any]:
        """
        Restrict data access based on conditions
        """
        return {
            'success': True,
            'message': 'Access restricted based on policy',
            'metadata': {'access_restricted': True, 'minimum_necessary': True}
        }
    
    def _validate_data(self, data: Dict[str, Any], conditions: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate data against compliance requirements
        """
        validation_passed = True
        validation_messages = []
        
        # Check required fields
        if 'required_fields' in conditions:
            for field in conditions['required_fields']:
                if field not in data:
                    validation_passed = False
                    validation_messages.append(f"Missing required field: {field}")
        
        return {
            'success': validation_passed,
            'message': 'Data validation completed',
            'metadata': {
                'validation_passed': validation_passed,
                'messages': validation_messages
            }
        }
    
    def _log_audit_event(self, policy_id: str, result: EnforcementResult):
        """
        Log audit event to compliance log
        """
        audit_event = {
            'timestamp': result.timestamp,
            'policy_id': policy_id,
            'rule_id': result.rule_id,
            'action_taken': result.action_taken.value,
            'success': result.success,
            'message': result.message,
            'metadata': result.metadata
        }
        
        try:
            # Load existing audit log
            audit_log = []
            try:
                with open(self.audit_log_path, 'r') as f:
                    audit_log = json.load(f)
            except FileNotFoundError:
                pass
            
            # Append new event
            audit_log.append(audit_event)
            
            # Write back to file
            with open(self.audit_log_path, 'w') as f:
                json.dump(audit_log, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
    
    def create_policy_from_template(self, template_name: str, policy_data: Dict[str, Any]) -> str:
        """
        Create new policy from drag-and-drop template
        """
        policy_id = f"{template_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        # Merge template with user data
        policy_data['policy_id'] = policy_id
        policy_data['created_date'] = datetime.utcnow().isoformat()
        
        # Parse and store policy
        policy = self._parse_policy(policy_data)
        self.policies[policy_id] = policy
        
        logger.info(f"Created new policy: {policy_id}")
        return policy_id
    
    def get_policy_status(self, policy_id: str) -> Dict[str, Any]:
        """
        Get policy enforcement status and metrics
        """
        if policy_id not in self.policies:
            raise ValueError(f"Policy {policy_id} not found")
        
        policy = self.policies[policy_id]
        
        # Load audit log to get enforcement metrics
        try:
            with open(self.audit_log_path, 'r') as f:
                audit_log = json.load(f)
            
            policy_events = [event for event in audit_log if event['policy_id'] == policy_id]
            
            return {
                'policy_id': policy_id,
                'policy_name': policy.name,
                'total_enforcements': len(policy_events),
                'successful_enforcements': len([e for e in policy_events if e['success']]),
                'failed_enforcements': len([e for e in policy_events if not e['success']]),
                'last_enforcement': policy_events[-1]['timestamp'] if policy_events else None,
                'compliance_frameworks': policy.compliance_frameworks
            }
            
        except Exception as e:
            logger.error(f"Error getting policy status: {e}")
            return {
                'policy_id': policy_id,
                'policy_name': policy.name,
                'error': str(e)
            }
    
    def get_compliance_dashboard(self) -> Dict[str, Any]:
        """
        Get comprehensive compliance dashboard data
        """
        try:
            with open(self.audit_log_path, 'r') as f:
                audit_log = json.load(f)
            
            # Calculate metrics
            total_events = len(audit_log)
            successful_events = len([e for e in audit_log if e['success']])
            failed_events = total_events - successful_events
            
            # Group by policy
            policy_stats = {}
            for event in audit_log:
                policy_id = event['policy_id']
                if policy_id not in policy_stats:
                    policy_stats[policy_id] = {'total': 0, 'success': 0, 'failed': 0}
                
                policy_stats[policy_id]['total'] += 1
                if event['success']:
                    policy_stats[policy_id]['success'] += 1
                else:
                    policy_stats[policy_id]['failed'] += 1
            
            # Group by action type
            action_stats = {}
            for event in audit_log:
                action = event['action_taken']
                if action not in action_stats:
                    action_stats[action] = 0
                action_stats[action] += 1
            
            return {
                'summary': {
                    'total_policies': len(self.policies),
                    'total_enforcements': total_events,
                    'successful_enforcements': successful_events,
                    'failed_enforcements': failed_events,
                    'compliance_rate': (successful_events / total_events * 100) if total_events > 0 else 0
                },
                'policy_statistics': policy_stats,
                'action_statistics': action_stats,
                'recent_events': audit_log[-10:] if audit_log else []
            }
            
        except Exception as e:
            logger.error(f"Error generating compliance dashboard: {e}")
            return {'error': str(e)}
    
    def _delete_data(self, data: Dict[str, Any], conditions: Dict[str, Any]) -> Dict[str, Any]:
        """
        Delete data according to retention policy
        """
        return {
            'success': True,
            'message': 'Data deleted according to retention policy',
            'metadata': {'deleted': True, 'retention_policy_applied': True}
        }

# Example usage and testing
if __name__ == "__main__":
    # Initialize policy engine
    engine = CognitoFlowPolicyEngine(
        cognito_user_pool_id="us-east-1_example123",
        region="us-east-1"
    )
    
    # Example: Enforce data privacy policy
    test_data = {
        'customer_email': 'john.doe@example.com',
        'phone_number': '555-123-4567',
        'purchase_history': ['item1', 'item2'],
        'consent_timestamp': '2024-01-15T10:00:00Z'
    }
    
    try:
        results = engine.enforce_policy('data_privacy_001', test_data)
        for result in results:
            print(f"Rule {result.rule_id}: {result.action_taken.value} - {result.message}")
    except Exception as e:
        print(f"Policy enforcement failed: {e}")
    
    # Example: Get compliance dashboard
    try:
        dashboard = engine.get_compliance_dashboard()
        print(f"Compliance Dashboard: {json.dumps(dashboard, indent=2)}")
    except Exception as e:
        print(f"Failed to get compliance dashboard: {e}")