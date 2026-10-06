from setuptools import find_packages, setup

package_name = 'unitac_collection'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='root',
    maintainer_email='root@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'test_robot_client = unitac_collection.test_robot_client:main',
            'genforce_cycle = unitac_collection.genforce_cycle_node:main',
            'test_gelsight_client = unitac_collection.test_gelsight_client:main',
            'test_capture = unitac_collection.test_capture:main',
            'genforce_collector = unitac_collection.genforce_collector_node:main',
            'genforce_single_cycle = unitac_collection.genforce_single_cycle_node:main',
        ],
    },
)
