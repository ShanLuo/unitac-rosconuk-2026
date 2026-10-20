from setuptools import setup, find_packages

package_name = 'unitac_representation'
setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Prof. Shan Luo',
    maintainer_email='shan.luo@kcl.ac.uk',
    description='GenForce tactile marker encoder for UniTac ROS 2.',
    license='MIT',
    entry_points={'console_scripts': [
        'genforce_encoder = unitac_representation.genforce_encoder_node:main',
        'marker_segmentation = unitac_representation.marker_segmentation_node:main',
        'adaptive_retraction = unitac_representation.adaptive_retraction_node:main',
    ]},
)
