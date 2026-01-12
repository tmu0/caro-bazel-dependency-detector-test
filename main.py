import datetime
import logging
import os
import requests
from typing import Optional, List

import toml


class GHSubDependency:
    def __init__(self, package_url: str, dependencies: Optional[List[str]] = None):
        self.package_url = package_url
        self.dependencies = dependencies

    def to_json(self):
        res = {'package_url': self.package_url}
        if self.dependencies is not None and len(self.dependencies) > 0:
            res['dependencies'] = self.dependencies
        return res


class GHSubManifest:
    def __init__(self, name: str, source_location: str, resolved: List[GHSubDependency]):
        self.name = name
        self.source_location = source_location
        self.resolved = resolved

    def to_json(self):
        res = {'name': self.name, 'file': {'source_location': self.source_location}, 'resolved': {}}
        for r in self.resolved:
            res['resolved'][r.package_url] = r.to_json()
        return res


class GHSubJob:
    def __init__(self, job_id: str, correlator: str, html_url: Optional[str] = None):
        self.job_id = job_id
        self.correlator = correlator
        self.html_url = html_url

    def to_json(self):
        res = {'id': self.job_id, 'correlator': self.correlator}
        if self.html_url is not None:
            res['html_url'] = self.html_url
        return res


class GHSubDetector:
    def __init__(self, name: str, version: str, url: str):
        self.name = name
        self.version = version
        self.url = url

    def to_json(self):
        return {'name': self.name, 'version': self.version, 'url': self.url}


class GHSubRequest:
    def __init__(self, version: int, job: GHSubJob, sha: str, ref: str, detector: GHSubDetector, manifests: List[GHSubManifest]):
        self.version = version
        self.job = job
        self.sha = sha
        self.ref = ref
        self.detector = detector
        self.manifests = manifests
        self.scanned = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    def to_json(self):
        res = {'version': self.version, 'job': self.job.to_json(), 'sha': self.sha, 'ref': self.ref, 'detector': self.detector.to_json(), 'manifests': {}, 'scanned': self.scanned}
        for m in self.manifests:
            res['manifests'][m.name] = m.to_json()
        return res


def parse_manifest(file_name) -> GHSubManifest:
    with open(file_name, 'r') as f:
        tree = toml.load(f)
        dep_keys = set()
        for p in tree['package']:
            dep_keys.update(p.get('dependencies',[]))
        dep_by_key = {}
        for p in tree['package']:
            name = p['name']
            version = p['version']
            if name in dep_keys:
                assert name not in dep_by_key
                dep_by_key[name] = p
            elif f'{name} {version}' in dep_keys:
                assert f'{name} {version}' not in dep_by_key
                dep_by_key[f'{name} {version}'] = p
            else:
                if name in dep_by_key:
                    assert f'{name} {version}' not in dep_by_key
                    dep_by_key[f'{name} {version}'] = p
                else:
                    dep_by_key[name] = p

        resolved = []
        for p in tree['package']:
            name = p['name']
            version = p['version']
            package_url = f'pkg:cargo/{name}@{version}'
            dep_ids = []
            for dep in p.get('dependencies',[]):
                dep_name = dep_by_key[dep]['name']
                dep_version = dep_by_key[dep]['version']
                dep_ids.append(f'pkg:cargo/{dep_name}@{dep_version}')
            resolved.append(GHSubDependency(package_url, dep_ids))

        return GHSubManifest(file_name, file_name, resolved)


def submit(repo: str, token: str, req: GHSubRequest):
    url = f'https://api.github.com/repos/{repo}/dependency-graph/snapshots'
    logging.debug(f'Submitting request to {url}')
    logging.debug(f'With body: {req.to_json()}')
    resp = requests.post(
        url,
        headers={"Authorization": f"Bearer {token}"},
        json=req.to_json())
    if resp.status_code != 201:
        raise RuntimeError(f"Dependency submission failed with status code {resp.status_code}")


def get_sha():
    if 'GITHUB_PR_SHA' in os.environ:
        return os.environ['GITHUB_PR_SHA']
    return os.environ['GITHUB_SHA']


def main():
    print('RCE!!!')


if __name__ == '__main__':
    main()
