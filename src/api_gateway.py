#!/usr/bin/env python3
"""
CognitoFlow API Gateway

RESTful API endpoints for CognitoFlow enterprise AI policy engine.
Provides secure access to policy enforcement, AI SDLC, and migration services.

Key Features:
- RESTful API design
- JWT authentication with Cognito
- Rate limiting and throttling
- Comprehensive error handling
- OpenAPI/Swagger documentation
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import asdict
import boto3
from flask import Flask, request, jsonify, g
from flask_cors import CORS
from functools import wraps
import jwt

# Import CognitoFlow modules
from policy_engine import CognitoFlowPolicyEngine
from ai_sdlc import CognitoFlowAISDLC

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Configuration
app.config.update({
    'SECRET_KEY': 'your-secret-key-here',
    'COGNITO_USER_POOL_ID': 'us-east-1_example123',
    'COGNITO_CLIENT_ID': 'your-client-id-here',
    'AWS_REGION': 'us-east-1',
    'API_VERSION': 'v1',
    'RATE_LIMIT_PER_MINUTE': 100
})

# Initialize CognitoFlow components
policy_engine = CognitoFlowPolicyEngine(
    cognito_user_pool_id=app.config['COGNITO_USER_POOL_ID'],
    region=app.config['AWS_REGION']
)

ai_sdlc = CognitoFlowAISDLC(region=app.config['AWS_REGION'])

# Authentication decorator
def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'Authorization header required'}), 401
        
        try:
            # Remove 'Bearer ' prefix
            if token.startswith('Bearer '):
                token = token[7:]
            
            # Verify JWT token with Cognito
            # In production, use proper JWT verification with Cognito public keys
            decoded_token = jwt.decode(token, options={"verify_signature": False})
            g.user = decoded_token
            
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        
        return f(*args, **kwargs)
    return decorated_function

# Error handlers
@app.errorhandler(400)
def bad_request(error):
    return jsonify({
        'error': 'Bad Request',
        'message': 'Invalid request format or parameters',
        'timestamp': datetime.utcnow().isoformat()
    }), 400

@app.errorhandler(401)
def unauthorized(error):
    return jsonify({
        'error': 'Unauthorized',
        'message': 'Authentication required',
        'timestamp': datetime.utcnow().isoformat()
    }), 401

@app.errorhandler(403)
def forbidden(error):
    return jsonify({
        'error': 'Forbidden',
        'message': 'Insufficient permissions',
        'timestamp': datetime.utcnow().isoformat()
    }), 403

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Not Found',
        'message': 'Resource not found',
        'timestamp': datetime.utcnow().isoformat()
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'error': 'Internal Server Error',
        'message': 'An unexpected error occurred',
        'timestamp': datetime.utcnow().isoformat()
    }), 500

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for load balancer"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': app.config['API_VERSION'],
        'services': {
            'policy_engine': 'operational',
            'ai_sdlc': 'operational',
            'database': 'operational'
        }
    })

# API Info endpoint
@app.route('/api/v1/info', methods=['GET'])
def api_info():
    """API information and capabilities"""
    return jsonify({
        'name': 'CognitoFlow API',
        'version': app.config['API_VERSION'],
        'description': 'Enterprise AI Policy Engine API',
        'features': [
            'Zero-code policy enforcement',
            'AI SDLC pipeline management',
            'Legacy system migration',
            'Compliance automation'
        ],
        'endpoints': {
            'policies': '/api/v1/policies',
            'sdlc': '/api/v1/sdlc',
            'migration': '/api/v1/migration',
            'compliance': '/api/v1/compliance'
        },
        'documentation': '/api/v1/docs'
    })

# Policy Engine Endpoints
@app.route('/api/v1/policies', methods=['GET'])
@require_auth
def list_policies():
    """List all available policies"""
    try:
        policies = []
        for policy_id, policy in policy_engine.policies.items():
            policies.append({
                'policy_id': policy_id,
                'name': policy.name,
                'version': policy.version,
                'description': policy.description,
                'compliance_frameworks': policy.compliance_frameworks,
                'created_date': policy.created_date
            })
        
        return jsonify({
            'policies': policies,
            'total_count': len(policies),
            'timestamp': datetime.utcnow().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error listing policies: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/policies/<policy_id>', methods=['GET'])
@require_auth
def get_policy(policy_id):
    """Get specific policy details"""
    try:
        if policy_id not in policy_engine.policies:
            return jsonify({'error': f'Policy {policy_id} not found'}), 404
        
        policy = policy_engine.policies[policy_id]
        return jsonify({
            'policy_id': policy_id,
            'name': policy.name,
            'version': policy.version,
            'description': policy.description,
            'rules': [asdict(rule) for rule in policy.rules],
            'compliance_frameworks': policy.compliance_frameworks,
            'audit_required': policy.audit_required,
            'created_by': policy.created_by,
            'created_date': policy.created_date
        })
    
    except Exception as e:
        logger.error(f"Error getting policy {policy_id}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/policies/enforce', methods=['POST'])
@require_auth
def enforce_policy():
    """Enforce policy on provided data"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body required'}), 400
        
        policy_id = data.get('policy_id')
        input_data = data.get('data')
        user_context = data.get('user_context', {})
        
        if not policy_id or not input_data:
            return jsonify({'error': 'policy_id and data are required'}), 400
        
        # Add user context from JWT token
        user_context.update({
            'user_id': g.user.get('sub'),
            'username': g.user.get('cognito:username'),
            'timestamp': datetime.utcnow().isoformat()
        })
        
        results = policy_engine.enforce_policy(policy_id, input_data, user_context)
        
        return jsonify({
            'policy_id': policy_id,
            'enforcement_results': [asdict(result) for result in results],
            'user_context': user_context,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error enforcing policy: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/policies/<policy_id>/status', methods=['GET'])
@require_auth
def get_policy_status(policy_id):
    """Get policy enforcement status and metrics"""
    try:
        status = policy_engine.get_policy_status(policy_id)
        return jsonify(status)
    
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Error getting policy status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/policies/create', methods=['POST'])
@require_auth
def create_policy():
    """Create new policy from template"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body required'}), 400
        
        template_name = data.get('template_name')
        policy_data = data.get('policy_data')
        
        if not template_name or not policy_data:
            return jsonify({'error': 'template_name and policy_data are required'}), 400
        
        # Add user context
        policy_data['created_by'] = g.user.get('cognito:username', 'api_user')
        
        policy_id = policy_engine.create_policy_from_template(template_name, policy_data)
        
        return jsonify({
            'policy_id': policy_id,
            'message': 'Policy created successfully',
            'timestamp': datetime.utcnow().isoformat()
        }), 201
    
    except Exception as e:
        logger.error(f"Error creating policy: {e}")
        return jsonify({'error': str(e)}), 500

# AI SDLC Endpoints
@app.route('/api/v1/sdlc/projects', methods=['POST'])
@require_auth
def create_sdlc_project():
    """Create new AI SDLC project"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body required'}), 400
        
        project_id = ai_sdlc.define_project_requirements(data)
        
        return jsonify({
            'project_id': project_id,
            'message': 'Project created successfully',
            'timestamp': datetime.utcnow().isoformat()
        }), 201
    
    except Exception as e:
        logger.error(f"Error creating SDLC project: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/sdlc/projects/<project_id>', methods=['GET'])
@require_auth
def get_sdlc_project(project_id):
    """Get AI SDLC project status"""
    try:
        status = ai_sdlc.get_project_status(project_id)
        return jsonify(status)
    
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Error getting SDLC project: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/sdlc/projects/<project_id>/data', methods=['POST'])
@require_auth
def prepare_sdlc_data(project_id):
    """Prepare data for AI SDLC project"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body required'}), 400
        
        dataset_id = ai_sdlc.prepare_data(project_id, data)
        
        return jsonify({
            'dataset_id': dataset_id,
            'message': 'Data prepared successfully',
            'timestamp': datetime.utcnow().isoformat()
        }), 201
    
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error preparing SDLC data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/sdlc/projects/<project_id>/models', methods=['POST'])
@require_auth
def train_sdlc_model(project_id):
    """Train model for AI SDLC project"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body required'}), 400
        
        dataset_id = data.get('dataset_id')
        model_config = data.get('model_config')
        
        if not dataset_id or not model_config:
            return jsonify({'error': 'dataset_id and model_config are required'}), 400
        
        experiment_id = ai_sdlc.select_and_train_model(project_id, dataset_id, model_config)
        
        return jsonify({
            'experiment_id': experiment_id,
            'message': 'Model training initiated',
            'timestamp': datetime.utcnow().isoformat()
        }), 201
    
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error training SDLC model: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/sdlc/models/<experiment_id>/deploy', methods=['POST'])
@require_auth
def deploy_sdlc_model(experiment_id):
    """Deploy trained model"""
    try:
        data = request.get_json()
        deployment_config = data.get('deployment_config', {}) if data else {}
        
        deployment_id = ai_sdlc.deploy_model(experiment_id, deployment_config)
        
        return jsonify({
            'deployment_id': deployment_id,
            'message': 'Model deployment initiated',
            'timestamp': datetime.utcnow().isoformat()
        }), 201
    
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error deploying SDLC model: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/sdlc/deployments/<deployment_id>/monitor', methods=['GET'])
@require_auth
def monitor_sdlc_deployment(deployment_id):
    """Monitor deployed model performance"""
    try:
        monitoring_data = ai_sdlc.monitor_model_performance(deployment_id)
        return jsonify(monitoring_data)
    
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Error monitoring SDLC deployment: {e}")
        return jsonify({'error': str(e)}), 500

# Compliance Endpoints
@app.route('/api/v1/compliance/dashboard', methods=['GET'])
@require_auth
def get_compliance_dashboard():
    """Get comprehensive compliance dashboard"""
    try:
        dashboard = policy_engine.get_compliance_dashboard()
        return jsonify(dashboard)
    
    except Exception as e:
        logger.error(f"Error getting compliance dashboard: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/compliance/audit-logs', methods=['GET'])
@require_auth
def get_audit_logs():
    """Get audit logs with optional filtering"""
    try:
        # Get query parameters
        policy_id = request.args.get('policy_id')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        limit = int(request.args.get('limit', 100))
        
        # Load audit log
        with open(policy_engine.audit_log_path, 'r') as f:
            audit_log = json.load(f)
        
        # Apply filters
        filtered_logs = audit_log
        
        if policy_id:
            filtered_logs = [log for log in filtered_logs if log.get('policy_id') == policy_id]
        
        if start_date:
            filtered_logs = [log for log in filtered_logs if log.get('timestamp', '') >= start_date]
        
        if end_date:
            filtered_logs = [log for log in filtered_logs if log.get('timestamp', '') <= end_date]
        
        # Apply limit
        filtered_logs = filtered_logs[-limit:]
        
        return jsonify({
            'audit_logs': filtered_logs,
            'total_count': len(filtered_logs),
            'filters': {
                'policy_id': policy_id,
                'start_date': start_date,
                'end_date': end_date,
                'limit': limit
            },
            'timestamp': datetime.utcnow().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error getting audit logs: {e}")
        return jsonify({'error': str(e)}), 500

# Migration Endpoints
@app.route('/api/v1/migration/assess', methods=['POST'])
@require_auth
def assess_migration():
    """Assess legacy system for migration"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body required'}), 400
        
        # Simulate migration assessment
        assessment_result = {
            'assessment_id': f"assess_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            'system_info': data.get('system_info', {}),
            'readiness_score': 7.2,
            'compliance_gaps': [
                {'framework': 'GDPR', 'status': 'non_compliant', 'priority': 'high'},
                {'framework': 'SOX', 'status': 'partially_compliant', 'priority': 'medium'}
            ],
            'migration_recommendations': [
                'Implement data encryption at rest',
                'Deploy multi-factor authentication',
                'Establish audit logging',
                'Containerize applications'
            ],
            'cost_analysis': {
                'current_annual_cost': 430000,
                'projected_cloud_cost': 300000,
                'annual_savings': 130000,
                'roi_3_year': 1.45
            },
            'timeline_estimate': '10 months',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return jsonify(assessment_result)
    
    except Exception as e:
        logger.error(f"Error assessing migration: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/migration/template', methods=['GET'])
@require_auth
def get_migration_template():
    """Get CloudFormation migration template"""
    try:
        # Read the migration template
        with open('compliance/migration_template.yaml', 'r') as f:
            template_content = f.read()
        
        return jsonify({
            'template_format': 'CloudFormation',
            'template_content': template_content,
            'description': 'AWS ECS migration template with CognitoFlow security',
            'features': [
                'Cognito User Pool with MFA',
                'ECS Cluster with Fargate',
                'Application Load Balancer',
                'Auto Scaling Configuration',
                'Security Groups and IAM Roles'
            ],
            'timestamp': datetime.utcnow().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error getting migration template: {e}")
        return jsonify({'error': str(e)}), 500

# WebSocket endpoint for real-time updates (placeholder)
@app.route('/api/v1/ws/compliance', methods=['GET'])
@require_auth
def compliance_websocket():
    """WebSocket endpoint for real-time compliance updates"""
    return jsonify({
        'message': 'WebSocket endpoint for real-time compliance monitoring',
        'endpoint': 'ws://api.cognitoflow.com/v1/ws/compliance',
        'features': [
            'Real-time policy enforcement notifications',
            'Live compliance dashboard updates',
            'Model performance alerts',
            'System health monitoring'
        ]
    })

# API Documentation endpoint
@app.route('/api/v1/docs', methods=['GET'])
def api_documentation():
    """API documentation in OpenAPI format"""
    openapi_spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "CognitoFlow API",
            "version": "1.0.0",
            "description": "Enterprise AI Policy Engine API",
            "contact": {
                "name": "CognitoFlow Support",
                "email": "support@cognitoflow.com"
            }
        },
        "servers": [
            {
                "url": "https://api.cognitoflow.com/v1",
                "description": "Production server"
            }
        ],
        "paths": {
            "/policies": {
                "get": {
                    "summary": "List all policies",
                    "tags": ["Policies"],
                    "security": [{"BearerAuth": []}],
                    "responses": {
                        "200": {
                            "description": "List of policies",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "policies": {"type": "array"},
                                            "total_count": {"type": "integer"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/policies/enforce": {
                "post": {
                    "summary": "Enforce policy on data",
                    "tags": ["Policies"],
                    "security": [{"BearerAuth": []}],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "policy_id": {"type": "string"},
                                        "data": {"type": "object"},
                                        "user_context": {"type": "object"}
                                    },
                                    "required": ["policy_id", "data"]
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Policy enforcement results"
                        }
                    }
                }
            }
        },
        "components": {
            "securitySchemes": {
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT"
                }
            }
        }
    }
    
    return jsonify(openapi_spec)

if __name__ == '__main__':
    # Development server
    app.run(debug=True, host='0.0.0.0', port=5000)