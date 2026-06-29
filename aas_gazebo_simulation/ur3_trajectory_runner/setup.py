from setuptools import find_packages, setup

package_name = 'ur3_trajectory_runner'

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
    maintainer='roboh',
    maintainer_email='roboh@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [ 'run_pick_place = ur3_trajectory_runner.run_pick_place:main',
        'pipeline3 = ur3_trajectory_runner.pipeline3:main', 
                            'record_joint_states = ur3_trajectory_runner.record_joint_states:main',
                            'run_pick_place_kpi = ur3_trajectory_runner.run_pick_place_kpi:main',
        ],
    },
)
