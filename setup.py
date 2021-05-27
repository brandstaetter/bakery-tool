from setuptools import find_packages, setup

setup(
  name="bakery_tool",
  description="A tool for Elite: Dangerous Bread Bakers",
  packages=find_packages(),
  install_requires=[
    "discord.py",
    "PyYAML",
    "python-dateutil",
    "tailer"
  ],
  setup_requires="setuptools_scm",
  use_scm_version=True
)
