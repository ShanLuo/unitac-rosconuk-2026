from setuptools import find_packages, setup

package_name = 'unitac_mg400'

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
    maintainer='Prof. Shan Luo',
    maintainer_email='shan.luo@kcl.ac.uk',
    description='ROS 2 interface and control nodes for the Dobot MG400 in UniTac.',
    license='MIT',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'mg400_state_node = unitac_mg400.mg400_state_node:main',
            'mg400_move_z_node = unitac_mg400.mg400_move_z_node:main',
        ],
    },
)
