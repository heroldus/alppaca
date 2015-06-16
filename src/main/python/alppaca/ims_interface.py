import requests

from util import init_logging


class NoRolesFoundException(Exception):
    pass


class IMSInterface(object):
    
    def __init__(self, ims_url, debug=False):
        self.ims_url = ims_url
        self.logger = init_logging(debug)

    def get_ims_credentials(self):
        pass

    def get_roles(self):
        try:
            response = requests.get("http://{0}/latest/meta-data/iam/security-credentials/".format(self.ims_url))

            if response.status_code == 200:
                if not response.content:
                    raise NoRolesFoundException("Server response was empty; host has no roles?")
                
                roles_list = [line.strip() for line in response.content.split("\n")] if response.content else []
                self.logger.debug("Loaded roles: {0}".format(roles_list))
                return roles_list
            else:
                response.raise_for_status()
        except Exception as e:
            self.logger.exception("Due to following cause:")
            raise NoRolesFoundException(e.message)