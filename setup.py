
import setuptools
import os

HERE = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(HERE, "requirements.txt")) as f:
    requirements = f.read().split("\n")

setuptools.setup(
    author="Ozan Mutlu",
    name="jenkins_setuptools_versioning",
    version=3.3,
    author_email="ozanmutluu@gmail.com",
    description="Use git repo data for building a version number according PEP-440",
    long_description="Handle versioning",
    long_description_content_type="text/markdown",
    url="https://github.com/ozanmutlu/jenkins_setuptools_versioning",
    packages=setuptools.find_packages(),
    python_requires='>=3.6',
    py_modules=["setuptools_git_versioning"],
    entry_points={
        "distutils.setup_keywords": [
            "version_config = setuptools_git_versioning:parse_config",
        ],
    },
    include_package_data=True,
    zip_safe=False,
    install_requires=requirements
)
