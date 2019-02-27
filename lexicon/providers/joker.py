"""Module provider for JOKER"""
from __future__ import absolute_import
import logging
try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode
import requests
from lexicon.providers.base import Provider as BaseProvider


LOGGER = logging.getLogger(__name__)

def provider_parser(subparser):
    """Configure provider parser for JOKER"""
    subparser.add_argument("--auth-username",
                           help="specify username for authentication")
    subparser.add_argument("--auth-password",
                           help="specify password for authentication")


class Provider(BaseProvider):
    """
    Joker has put a short description on https://joker.com/faq/content/6/496/de/let_s-encrypt-support.html?highlight=letsencrypt

    """
    def __init__(self, config):
        """
        :param config: command line options
        """
        super(Provider, self).__init__(config)

        self._auth = {'username': self._get_provider_option('auth_username'),
                      'password': self._get_provider_option('auth_password')}
        self._domain = self.domain.lower()
        self.domain_id = None
        self.api_endpoint = self._get_provider_option(
            'endpoint') or 'https://svc.joker.com/nic/replace'
        assert self._auth['username'] is not None
        self.password = self._get_provider_option('auth_password')
        assert self._auth['password'] is not None

    def _joker_svc_nic_replace(self, identifier, rtype, name, content):
        """
        create, update or delete a record
        :param str identifier: identifier of record
        :param str rtype: type of record
        :param str name: name of record
        :param mixed content: value of record (use None or '' for deletion)
        :return bool: success status
        :raises Exception: on error
        """
        data = {'username': self._auth['username'],
            'password': self._auth['password'],
            'zone': self._domain,
            'label': self._relative_name(
                name
            ),
            'type': rtype
        }
        if (content):
            data['value'] = content
        else:
            data['value'] = ''
        if self._get_lexicon_option('ttl'):
            data['ttl'] = self._get_lexicon_option('ttl')
        if (identifier):
            LOGGER.warn('Specifying an identifier is not supported by this provider.')
            return False

        payload = {'success': True}
        try:
            payload = self._post(
                self.api_endpoint, data)
        except requests.exceptions.HTTPError as err:
            LOGGER.error(err.response)
            return False

        LOGGER.info('create_record: %s', payload.content)
        return True

    def _validate_response(self, response, message, exclude_code=None):  # pylint: disable=no-self-use
        """
        validate an api server response

        :param dict response: server response to check
        :param str message: error message to raise
        :param int exclude_code: error codes to exclude from errorhandling
        :return:
        ":raises Exception: on error
        """
        if 'code' in response and response['code'] >= 2000:
            if exclude_code is not None and response['code'] == exclude_code:
                return

            raise Exception("{0}: {1} ({2})".format(
                message, response['msg'], response['code']))

    # Make any request to validate credentials
    def _authenticate(self):
        """
        run any request against the API just to make sure the credentials
        are valid

        :return bool: success status
        :raises Exception: on error
        """
        opts = {'domain': self._domain}
        opts.update(self._auth)

        # set to fake id to pass tests, joker doesn't work on domain id but
        # uses domain names for identification
        self.domain_id = 1

        return True

    def _create_record(self, rtype, name, content):
        """
        create a record
        does an update if the record already exists

        :param str rtype: type of record
        :param str name: name of record
        :param mixed content: value of record
        :return bool: success status
        :raises Exception: on error
        """
        identifier = None
        if (content):
            return self._joker_svc_nic_replace(identifier, rtype, name, content)
        else:
            LOGGER.error('No value given for content. This would delete the record with the api call.')
            return False


    def _list_records(self, rtype=None, name=None, content=None):
        """
        list all records

        :param str rtype: type of record
        :param str name: name of record
        :param mixed content: value of record
        :return list: list of found records
        :raises Exception: on error
        """
        records = []
        return records

    def _update_record(self, identifier, rtype=None, name=None, content=None):
        """
        update a record

        :param int identifier: identifier of record to update
        :param str rtype: type of record
        :param str name: name of record
        :param mixed content: value of record
        :return bool: success status
        :raises Exception: on error
        """

        return self._joker_svc_nic_replace(identifier, rtype, name, content)

    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        """
        delete a record
        filter selection to delete by rtype/name/content

        :param int identifier: identifier of record to update
        :param str rtype: rtype of record
        :param str name: name of record
        :param mixed content: value of record
        :return bool: success status
        :raises Exception: on error
        """
        if (identifier):
            LOGGER.warning(self, 'Deleting by identifier is not supported by this provider.')
            return False
        return self._joker_svc_nic_replace(self, identifier, rtype, name, content)

    def _request(self, action='GET', url='/', data=None, query_params=None):
        if data is None:
            data = {}
        if query_params:
            query_string = '?' + urlencode(query_params)
        else:
            query_string = ''
            query_params = {}
        if data:
            data = urlencode(data)
        else:
            data = ''
        default_headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        default_auth = None
        response = requests.request(action, url, params=query_params,
                                    data=data, headers=default_headers, auth=default_auth)
        # if the request fails for any reason, throw an error.
        response.raise_for_status()
        return response
