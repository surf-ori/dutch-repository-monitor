
import requests
import yaml
import pandas as pd
from requests.auth import HTTPBasicAuth
import time
import logging
from datetime import datetime, timedelta
import json
from pathlib import Path

class OpenAIREClient:
    """Client for interacting with OpenAIRE Graph API"""
    
    def __init__(self, config):
        self.config = config
        self.client_id = config['CLIENT_ID']
        self.client_secret = config['CLIENT_SECRET']
        self.api_base_url = config['OpenAIRE_API'] 
        self.auth_url = config['auth_url']
        self.access_token = None
        self.token_expires_at = None
        
        # Setup comprehensive logging
        self.setup_logging()
        
        # Initialize API request counter for this session
        self.request_counter = 0
    
    def setup_logging(self):
        """Setup comprehensive API logging system"""
        try:
            # Create logs directory
            self.logs_dir = Path("logs")
            self.logs_dir.mkdir(exist_ok=True)
            
            # Setup standard logger
            logging.basicConfig(level=logging.INFO)
            self.logger = logging.getLogger(__name__)
            
            # Setup API-specific logger for detailed request/response logging
            self.api_logger = logging.getLogger(f"{__name__}.api")
            self.api_logger.setLevel(logging.INFO)
            
            # Create API log file handler with date-based naming
            today = datetime.now().strftime('%Y%m%d')
            api_log_file = self.logs_dir / f"api_requests_{today}.log"
            
            # Create file handler if it doesn't exist
            if not hasattr(self, '_api_file_handler') or self._current_log_date != today:
                if hasattr(self, '_api_file_handler'):
                    self.api_logger.removeHandler(self._api_file_handler)
                
                self._api_file_handler = logging.FileHandler(api_log_file)
                self._api_file_handler.setLevel(logging.INFO)
                
                # Create detailed formatter for API logs
                api_formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
                self._api_file_handler.setFormatter(api_formatter)
                self.api_logger.addHandler(self._api_file_handler)
                self._current_log_date = today
            
            # Prevent duplicate logs in root logger
            self.api_logger.propagate = False
            
        except Exception as e:
            print(f"Error setting up logging: {e}")
            # Fallback to basic logging
            self.logger = logging.getLogger(__name__)
            self.api_logger = self.logger
    
    def log_api_request(self, method, url, params=None, headers=None, response=None, 
                       start_time=None, end_time=None, error=None, context=None):
        """Log detailed API request and response information"""
        try:
            self.request_counter += 1
            
            # Calculate response time
            response_time_ms = None
            if start_time and end_time:
                response_time_ms = round((end_time - start_time) * 1000, 2)
            
            # Create structured log entry
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "request_id": f"req_{self.request_counter}_{int(time.time())}",
                "method": method,
                "url": url,
                "parameters": params or {},
                "context": context or {},
                "response_time_ms": response_time_ms,
                "success": error is None and (response is not None and hasattr(response, 'status_code') and response.status_code == 200)
            }
            
            # Add response information
            if response is not None:
                log_entry.update({
                    "status_code": getattr(response, 'status_code', None),
                    "response_headers": dict(getattr(response, 'headers', {})),
                    "response_size_bytes": len(getattr(response, 'content', b''))
                })
                
                # Add response content (truncated for large responses)
                try:
                    if hasattr(response, 'json'):
                        response_json = response.json()
                        # Truncate large responses for logging
                        if isinstance(response_json, dict):
                            if 'results' in response_json and isinstance(response_json['results'], list):
                                # Log summary for results arrays
                                log_entry["response_summary"] = {
                                    "total_results": response_json.get('total', len(response_json['results'])),
                                    "returned_results": len(response_json['results']),
                                    "has_more": response_json.get('hasMore', False)
                                }
                                # Include first result as sample (truncated)
                                if response_json['results']:
                                    first_result = response_json['results'][0]
                                    log_entry["sample_result"] = str(first_result)[:500] + "..." if len(str(first_result)) > 500 else first_result
                            else:
                                # For non-results responses, log the full content (truncated)
                                response_str = str(response_json)
                                log_entry["response_content"] = response_str[:1000] + "..." if len(response_str) > 1000 else response_json
                    else:
                        # For non-JSON responses
                        response_text = getattr(response, 'text', '')
                        log_entry["response_content"] = response_text[:500] + "..." if len(response_text) > 500 else response_text
                        
                except Exception as json_error:
                    log_entry["response_parse_error"] = str(json_error)
                    log_entry["response_content"] = getattr(response, 'text', '')[:200]
            
            # Add error information
            if error is not None:
                log_entry.update({
                    "error": str(error),
                    "error_type": type(error).__name__
                })
            
            # Log as JSON string
            self.api_logger.info(json.dumps(log_entry, indent=2))
            
            # Also log summary to standard logger
            status = "SUCCESS" if log_entry["success"] else "FAILED"
            summary = f"API {method} {status}: {url}"
            if response_time_ms:
                summary += f" ({response_time_ms}ms)"
            if hasattr(response, 'status_code'):
                summary += f" [HTTP {response.status_code}]"
            
            if log_entry["success"]:
                self.logger.info(summary)
            else:
                self.logger.error(summary)
                
        except Exception as logging_error:
            # Fallback logging if structured logging fails
            self.logger.error(f"Error in API logging: {logging_error}")
            if response:
                self.logger.info(f"API Request: {method} {url} -> {getattr(response, 'status_code', 'Unknown')}")
    
    def get_access_token(self):
        """Get or refresh the access token"""
        start_time = time.time()
        response = None
        error = None
        
        try:
            # Check if we need a new token
            if (self.access_token is None or 
                self.token_expires_at is None or 
                datetime.now() >= self.token_expires_at):
                
                self.logger.info("Requesting new access token...")
                
                response = requests.post(
                    self.auth_url,
                    data={'grant_type': 'client_credentials'},
                    auth=HTTPBasicAuth(self.client_id, self.client_secret),
                    timeout=30
                )
                
                end_time = time.time()
                
                # Log the authentication request
                self.log_api_request(
                    method="POST",
                    url=self.auth_url,
                    params={"grant_type": "client_credentials"},
                    response=response,
                    start_time=start_time,
                    end_time=end_time,
                    context={"operation": "get_access_token", "token_refresh": True}
                )
                
                if response.status_code == 200:
                    token_data = response.json()
                    self.access_token = token_data.get('access_token')
                    expires_in = token_data.get('expires_in', 3600)  # Default 1 hour
                    self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 300)  # 5 min buffer
                    self.logger.info("Access token obtained successfully")
                    return self.access_token
                else:
                    self.logger.error(f"Failed to get access token: {response.status_code}")
                    return None
            
            # Return existing valid token
            return self.access_token
            
        except Exception as e:
            error = e
            end_time = time.time()
            
            # Log the failed authentication request
            self.log_api_request(
                method="POST",
                url=self.auth_url,
                params={"grant_type": "client_credentials"},
                response=response,
                start_time=start_time,
                end_time=end_time,
                error=error,
                context={"operation": "get_access_token", "token_refresh": True}
            )
            
            self.logger.error(f"Error getting access token: {e}")
            return None
    
    def make_authenticated_request(self, url, params=None, context=None):
        """Make an authenticated request to the OpenAIRE API"""
        start_time = time.time()
        response = None
        error = None
        retry_attempted = False
        
        token = self.get_access_token()
        if not token:
            # Log failed request due to no token
            self.log_api_request(
                method="GET",
                url=url,
                params=params,
                start_time=start_time,
                end_time=time.time(),
                error="No access token available",
                context=context or {}
            )
            return None
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            end_time = time.time()
            
            if response.status_code == 200:
                # Log successful request
                self.log_api_request(
                    method="GET",
                    url=url,
                    params=params,
                    headers=headers,
                    response=response,
                    start_time=start_time,
                    end_time=end_time,
                    context=context or {}
                )
                return response.json()
                
            elif response.status_code == 401:
                # Token might be expired, try once more
                self.logger.info("Token appears expired, attempting refresh...")
                self.access_token = None
                token = self.get_access_token()
                
                if token:
                    retry_attempted = True
                    retry_start = time.time()
                    headers['Authorization'] = f'Bearer {token}'
                    response = requests.get(url, headers=headers, params=params, timeout=30)
                    retry_end = time.time()
                    
                    # Log the retry attempt
                    retry_context = (context or {}).copy()
                    retry_context.update({"retry_attempt": True, "original_status": 401})
                    
                    self.log_api_request(
                        method="GET",
                        url=url,
                        params=params,
                        headers=headers,
                        response=response,
                        start_time=retry_start,
                        end_time=retry_end,
                        context=retry_context
                    )
                    
                    if response.status_code == 200:
                        return response.json()
            
            # Log failed request
            failed_context = (context or {}).copy()
            failed_context.update({"retry_attempted": retry_attempted})
            
            self.log_api_request(
                method="GET",
                url=url,
                params=params,
                headers=headers,
                response=response,
                start_time=start_time,
                end_time=end_time,
                context=failed_context
            )
            
            self.logger.error(f"API request failed: {response.status_code} - {response.text[:200]}")
            return None
            
        except Exception as e:
            error = e
            end_time = time.time()
            
            # Log exception
            exception_context = (context or {}).copy()
            exception_context.update({"retry_attempted": retry_attempted})
            
            self.log_api_request(
                method="GET",
                url=url,
                params=params,
                headers=headers,
                response=response,
                start_time=start_time,
                end_time=end_time,
                error=error,
                context=exception_context
            )
            
            self.logger.error(f"Error making API request: {e}")
            return None
    
    def get_organization_id(self, ror_link):
        """Get OpenAIRE organization ID from ROR link"""
        try:
            url = f"{self.api_base_url}organizations"
            params = {'pid': ror_link}
            context = {
                "operation": "get_organization_id",
                "ror_link": ror_link,
                "endpoint": "organizations"
            }
            
            response = self.make_authenticated_request(url, params, context)
            if response and 'results' in response:
                for result in response['results']:
                    org_id = result.get('id', '')
                    if org_id.startswith('openorgs____::'):
                        self.logger.info(f"Found organization ID {org_id} for ROR link {ror_link}")
                        return org_id
            
            self.logger.warning(f"No organization ID found for ROR link {ror_link}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting organization ID for {ror_link}: {e}")
            return None
    
    def get_organization_publications(self, org_id, from_date=None, to_date=None):
        """Get publications for an organization"""
        try:
            url = f"{self.api_base_url}results"
            params = {
                'format': 'json',
                'size': 100,
                'sortBy': 'dateofcollection',
                'sortOrder': 'desc'
            }
            
            # Add organization filter
            if org_id:
                params['fq'] = f'(reltypevalue exact "isProducedBy") AND (relorganizationid exact "{org_id}")'
            
            # Add date filters if provided
            if from_date:
                params['from'] = from_date.strftime('%Y-%m-%d')
            if to_date:
                params['to'] = to_date.strftime('%Y-%m-%d')
            
            context = {
                "operation": "get_organization_publications",
                "org_id": org_id,
                "endpoint": "results",
                "date_filter": {
                    "from_date": from_date.strftime('%Y-%m-%d') if from_date else None,
                    "to_date": to_date.strftime('%Y-%m-%d') if to_date else None
                }
            }
            
            response = self.make_authenticated_request(url, params, context)
            if response:
                total_results = response.get('total', 0)
                returned_results = len(response.get('results', []))
                self.logger.info(f"Retrieved {returned_results} publications (of {total_results} total) for organization {org_id}")
                return response
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting publications for {org_id}: {e}")
            return None
    
    def get_data_sources(self, org_id):
        """Get data sources for an organization"""
        try:
            url = f"{self.api_base_url}datasources"
            params = {
                'format': 'json',
                'size': 50
            }
            
            if org_id:
                params['fq'] = f'relorganizationid exact "{org_id}"'
            
            context = {
                "operation": "get_data_sources",
                "org_id": org_id,
                "endpoint": "datasources"
            }
            
            response = self.make_authenticated_request(url, params, context)
            if response:
                data_source_count = len(response.get('results', []))
                self.logger.info(f"Retrieved {data_source_count} data sources for organization {org_id}")
                return response
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting data sources for {org_id}: {e}")
            return None
    
    def get_organization_stats(self, org_id):
        """Get comprehensive statistics for an organization"""
        start_time = time.time()
        
        try:
            self.logger.info(f"Starting comprehensive stats collection for organization {org_id}")
            
            stats = {
                'org_id': org_id,
                'timestamp': datetime.now(),
                'publications_total': 0,
                'publications_recent': 0,
                'data_sources_count': 0,
                'last_publication_date': None,
                'repository_health': 'unknown',
                'data_freshness_days': None
            }
            
            # Get publications
            publications = self.get_organization_publications(org_id)
            if publications and 'results' in publications:
                stats['publications_total'] = publications.get('total', 0)
                
                # Count recent publications (last 30 days)
                recent_date = datetime.now() - timedelta(days=30)
                recent_count = 0
                last_pub_date = None
                
                for pub in publications['results'][:50]:  # Check first 50 results
                    pub_date_str = pub.get('dateofcollection')
                    if pub_date_str:
                        try:
                            pub_date = datetime.strptime(pub_date_str[:10], '%Y-%m-%d')
                            if pub_date >= recent_date:
                                recent_count += 1
                            if not last_pub_date or pub_date > last_pub_date:
                                last_pub_date = pub_date
                        except:
                            pass
                
                stats['publications_recent'] = recent_count
                stats['last_publication_date'] = last_pub_date
                
                # Calculate data freshness
                if last_pub_date:
                    stats['data_freshness_days'] = (datetime.now() - last_pub_date).days
            
            # Get data sources
            data_sources = self.get_data_sources(org_id)
            if data_sources and 'results' in data_sources:
                stats['data_sources_count'] = len(data_sources['results'])
            
            # Determine repository health
            if stats['data_freshness_days'] is not None:
                if stats['data_freshness_days'] <= 7:
                    stats['repository_health'] = 'healthy'
                elif stats['data_freshness_days'] <= 30:
                    stats['repository_health'] = 'warning'
                else:
                    stats['repository_health'] = 'critical'
            
            end_time = time.time()
            processing_time = round((end_time - start_time) * 1000, 2)
            
            self.logger.info(f"Completed stats collection for {org_id} in {processing_time}ms: "
                           f"{stats['publications_total']} total pubs, "
                           f"{stats['publications_recent']} recent, "
                           f"{stats['data_sources_count']} data sources, "
                           f"health: {stats['repository_health']}")
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting organization stats for {org_id}: {e}")
            return None
    
    def test_connection(self):
        """Test the API connection"""
        try:
            self.logger.info("Testing API connection...")
            
            token = self.get_access_token()
            if token:
                # Test with a simple organizations query
                url = f"{self.api_base_url}organizations"
                params = {'size': 1}
                context = {
                    "operation": "test_connection",
                    "endpoint": "organizations",
                    "test_query": True
                }
                
                response = self.make_authenticated_request(url, params, context)
                
                if response is not None:
                    self.logger.info("✓ API connection test successful")
                    return True
                else:
                    self.logger.error("✗ API connection test failed - no response")
                    return False
            else:
                self.logger.error("✗ API connection test failed - no access token")
                return False
                
        except Exception as e:
            self.logger.error(f"✗ API connection test failed with exception: {e}")
            return False
