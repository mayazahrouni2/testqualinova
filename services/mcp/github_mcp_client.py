from datetime import datetime

class GithubMCPClient:
    """ Simulateur de connexion à un MCP GitHub/GitLab. """

    def __init__(self):
        # Mocks isolés par company
        self.mock_db = {
            "test_company": {
                "repos": {
                    "backend-api": {
                        "branch_protection": True,
                        "required_reviews": True,
                        "status_checks": True,
                        "mfa_enforced": True,
                        "secret_scanning": False,
                        "roles": ["admin", "dev"],
                        "pipelines": ["build", "test", "deploy"]
                    }
                }
            },
            "tech_corp": {
                "repos": {
                    "frontend-app": {
                        "branch_protection": False,  # non-conforme
                        "required_reviews": False,
                        "status_checks": False,
                        "mfa_enforced": True,
                        "secret_scanning": False,
                        "roles": ["admin", "dev"],
                        "pipelines": ["build"]
                    }
                }
            }
        }

    def _get_company_repos(self, company_id: str) -> dict:
        company_data = self.mock_db.get(company_id, {})
        return company_data.get("repos", {})

    def get_repo_security_config(self, company_id: str) -> dict:
        """ Retourne les configurations de sécurité globales des repos de la company. """
        repos = self._get_company_repos(company_id)
        if not repos:
            return {}
        
        # Pour simplifier, on prend le premier repo configuré
        repo_name = list(repos.keys())[0]
        repo_data = repos[repo_name]

        return {
            "source": "github_mcp",
            "repo": repo_name,
            "branch": "main",
            "branch_protection": repo_data.get("branch_protection", False),
            "required_reviews": repo_data.get("required_reviews", False),
            "status_checks": repo_data.get("status_checks", False),
            "mfa_enforced": repo_data.get("mfa_enforced", False),
            "secret_scanning": repo_data.get("secret_scanning", False),
            "timestamp": datetime.now().strftime("%Y-%m-%d")
        }

    def get_branch_protection(self, company_id: str, repo: str) -> dict:
        """ branch protection, required reviewers, status checks """
        repos = self._get_company_repos(company_id)
        repo_data = repos.get(repo, {})
        return {
            "branch_protection": repo_data.get("branch_protection", False),
            "required_reviews": repo_data.get("required_reviews", False),
            "status_checks": repo_data.get("status_checks", False),
        }

    def get_access_control(self, company_id: str, repo: str) -> dict:
        """ membres, rôles (admin/dev), MFA enforced """
        repos = self._get_company_repos(company_id)
        repo_data = repos.get(repo, {})
        return {
            "roles": repo_data.get("roles", []),
            "mfa_enforced": repo_data.get("mfa_enforced", False),
        }

    def get_ci_cd_config(self, company_id: str, repo: str) -> dict:
        """ pipelines, checks obligatoires """
        repos = self._get_company_repos(company_id)
        repo_data = repos.get(repo, {})
        return {
            "pipelines": repo_data.get("pipelines", []),
            "status_checks": repo_data.get("status_checks", False),
        }

    def get_secret_scanning(self, company_id: str, repo: str) -> dict:
        """ status du secret scanning """
        repos = self._get_company_repos(company_id)
        repo_data = repos.get(repo, {})
        return {
            "secret_scanning": repo_data.get("secret_scanning", False),
        }

github_mcp_client = GithubMCPClient()
