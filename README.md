# mpbp-instances
The Multi-Period Blending Problem (MPBP) is a network optimization problem that involves routing fluid within a set of tanks based on inlet flows, concentrations and demand specifications. The goal is to maximize operational profit while meeting demand specifications. The network generally includes a set of supply tanks, blending tanks and demand tanks. A figure is shown below of a general MPBP network architecture. For more information about the problem, model and decompositions please refer to our [paper](https://pubs.acs.org/doi/10.1021/acs.iecr.5c02853).

<img width="1094" height="649" alt="image" src="https://github.com/user-attachments/assets/80e67857-0884-4d7f-9615-a31feecd661d" />

This repository contains 60 instances that can be used by the community to benchmark models and algorithms applied to the blending problem. The instances can be found under the [instances_json](instances_json/) folder. You can clone this repository to access the instances and code.

Along with this we have provided a Pyomo model for the monolithic MIQCP formulation that was proposed by Kolodziej et. al. [1] which can be found in [miqcp.py](miqcp.py)
Currently, the script is set to solve instance 6, however you can change which instance you want to solve by editing that within the file. The `convert_json_to_data()` function allows you to convert the json file to a `dict` format readable for the model. 

If you want to generate your own instance you can do so using the `InstanceGenerator` class found in [instance_generator.py](instance_generator.py). The instance generator takes information about the number of supply tanks, demand tanks, time periods, components, layout of the blending tanks and the time at what demand begins. If you want to see a mathematical description of the instance generation algorithm please refer to [instance_sizes](instance_sizes.pdf), or to the Supplimental Information section of our paper.

The 60 instances have been generated to be more challenging than those found in literature. Some information about the set sizes can be found below:
| Set            | Size Range |
|----------------|:----------:|
| Supply Tanks   | 2-5        |
| Blending Tanks | 5-15       |
| Demand Tanks   | 2-4        |
| Components     | 1-10       |
| Time Periods   | 5-30       |

## Citation
If you are interested in our work and decide to use our instances, please cite our work:

```
@article{doi:10.1021/acs.iecr.5c02853,
author = {Ovalle, Daniel and Bhatia, Arsh and Laird, Carl D. and Grossmann, Ignacio E.},
title = {A Logic-Based Decomposition for the Global Optimization of the Multiperiod Blending Problem Using Symmetry-Breaking Cuts},
journal = {Industrial \& Engineering Chemistry Research},
volume = {65},
number = {7},
pages = {3981-3998},
year = {2026},
doi = {10.1021/acs.iecr.5c02853}
}
```

## References
[1] Kolodziej S.P., Grossmann I.E., Furman K.C., Sawaya N.W., "A discretization-based approach for the optimization of the multiperiod blend scheduling problem", Computers and Chemical Engineering, 2013. [DOI](https://doi.org/10.1016/j.compchemeng.2013.01.016)



