#!/usr/bin/python

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

hib_classifiers = [
    "License :: OSI Approved :: MIT License",
    "Topic :: Utilities",
]

with open("README.md", "r") as fp:
    hib_long_description = fp.read()

setup(name="hibagent",
      version='1.1.0',
      author="Aleksei Besogonov",
      author_email="cyberax@amazon.com",
      url="https://github.com/awslabs/hibagent",
      tests_require=["pytest"],
      scripts=['agent/hibagent', 'agent/enable-ec2-spot-hibernation'],
      data_files=[('/etc', ['etc/hibagent-config.cfg']),
                  ('/etc/init.d', ['etc/init.d/hibagent'])],
      test_suite='test',
      description="Hibernation Trigger for EC2 Spot Instances",
      long_description=hib_long_description,
      license="Apache 2.0",
      classifiers=hib_classifiers
)
