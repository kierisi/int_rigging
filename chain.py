from maya import cmds

def fkchain(parent, joints, template, color):
    joint_parent = parent

    # joints = cmds.ls(sl=True)
    # will print out the names of all joints selected in the outliner
        
    for jnt in joints:
        
        # create a control and a group for each joint and rename group and control
        grp, ctl = create_control_from_template(jnt.replace("jnt", "ctl"), joint_parent, template, color)
            
        # position the control on the joint
        #cmds.matchTransform(ctl, jnt) 
        cmds.delete(cmds.parentConstraint(jnt, grp, mo=False))
        
        joint_parent = ctl  # update value of joint_parent to 'ctl' 
            
        # drive the joint
        cmds.pointConstraint(ctl, jnt)
        cmds.orientConstraint(ctl, jnt)
        cmds.scaleConstraint(ctl, jnt)

for side in ["lf", "rt"]:
    for phalanx in ["A", "B", "C", "D", "E"]:
        joints = []
        for i in range(4):
            jnt_name = "{0}_finger{1}0{2}_jnt".format(side, phalanx, i)
            if cmds.objExists(jnt_name):
                joints.append(jnt_name)

def create_control_from_template(name, parent, template, color):
    # create a control and a group for each joint and rename group and control
    grp, ctl = cmds.duplicate(template, n=name.replace("ctl", "grp"), rc=True)
    # rc = rename children
    ctl = cmds.rename(ctl, name)

    # parent group under the previous control
    if parent:    # if joint_parent has a value, execute next line
        cmds.parent(grp, parent)
    
    cmds.setAttr("{0}.overrideEnabled".format(ctl), 1)
    cmds.setAttr("{0}.overrideColor".format(ctl), color)

    return grp, ctl

def ikchain(name, side, joints, iktemplate, pvtemplate, color):