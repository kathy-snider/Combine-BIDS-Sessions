# Combine-BIDS-Sessions

Sometimes multiple sessions for a subject need to be collapsed into a single
session before being processed through a pipeline. When this occurs,
Combine-BIDS-Sessions(CBS) can be used.

The user specifies a subject, and CBS uses BIDSLayout
([pybids](https://bids-standard.github.io/pybids/)) to find all of the sessions
for that subject. If the user specifies the session-list argument, the sessions will 
be combined in the order specified in the list. If the user does not provide a
session list, all of the sessions for the subject will be combined, in the order
determined by BIDSLayout. (Order matters here; see Functional Data below.)

### Anatomical Data
All T1w and T2w files found in the list of sessions will be copied to the new anat
subdirectory. If the user wants to limit T1ws or T2ws to those from a specific
session, that can be done with the t1-session-label or t2-session-label
argument. A run number will be added to the name of each file to avoid name
collisions.

### Functional Data
Functional files are renumbered within each task. (That is, all task-rest files
from the list of sessions are numbered uniquely, all task-nback files are
numbered uniquely, and so on.) The files for each task are numbered sequentially
using run numbers, starting at 1. The runs within each task are numbered as they
are discovered, so this is where the order of the sessions (as noted above)
matters. All of the runs from the second original session will have run numbers 
that are greater than those from the first original session and less than those
from the third original session. Within each original session the runs will be
kept in order (by BIDSLayout).

### Field Maps
Each field map file found in the list of sessions is assigned a run-number and
copied to the new fmap subdirectory.

## The New Dataset
The new dataset is written to the same directory level as the original dataset.
That is, if your BIDS data is in datapath/niftis, the combined dataset is
written to datapath/niftis_desc-combined. The word "combined" (i.e., the desc-
keyword's value) can be replaced with another description, by using the
dataset-name argument. There is no session directory level in the new dataset,
so each subject has its BIDS subdirectories (anat, fmap, and func) directly
under its sub-LABEL directory.

As each nii file is copied, with its new name to its new location, its sidecar
json is also copied using the corresponding basename. Each original file and new 
file are logged to track the relationship.

## Group Ownership
If the user specifies the owner-group argument, `chgrp`, using that value, will
be applied as each directory is created. Otherwise the operating system's
default owner assignment will be left alone.

## Usage
Combine-BIDS-Sessions has the following command line arguments:

```{bash}
usage: run.py [-h] [--session-list SESSION-LABEL [SESSION-LABEL ...]]
              [--t1-session-label T1_SESSION_LABEL]
              [--t2-session-label T2_SESSION_LABEL]
              [--dataset-name DATASET_NAME] [--owner-group OWNER_GROUP]
              bids_dir participant_label

    Combines data from multiple sessions for one subject so that it can be
processed
    as though it were a single session. To do this:

      - Anatomy data will be combined into one directory. The user can specify a
        session
        where T1w data can be found. Otherwise, all T1w data found in the
sessions being
        combined will be used. T1w file will be assigned a run number (in the
order
        found) and this run number will replace the session number in the
filename.
        Likewise for T2w data.

      - All functional data for the subject will be combined into a single
        directory by
        copying the data. The task files will be renumbered such that those for
the same
        task-<TASKNAME> will have sequential runs. For example, if
        sub-X_ses-Y_task-rest_run-1 through sub-X_ses-Y_task-rest_run-m and
        sub-X_ses-Z_task-rest_run-1 through sub-X_ses-Z_task-rest_run-n are
found, then
        sub-X_task-rest_run-1 through sub-X_task-rest_run-(m+n)
        will be written to the func subdirectory of the combined session.
        A metadata field, called SourceFile, in the .json file associated with
each file
        written will point back to the original file from which the data was
copied.

      - Multiple fmap files can be present, and the 'IntendedFor' field (if any)
        in the
        metadata for each fmap file will be updated to match the new path in the
combined
        session.



positional arguments:
  bids_dir              Full path to the directory with the input BIDS-
                        formatted data set. Data must be in BIDS format.
  participant_label     The label of the participant to be processed. The
                        label corresponds to sub-<participant_label> from the
                        BIDS specification (i.e.,does not include "sub-").

optional arguments:
  -h, --help            show this help message and exit
  --session-list SESSION-LABEL [SESSION-LABEL ...]
                        The labels for the list of sessions to be combined, in
                        the order in which their runs should be processed.
                        Each label corresponds to ses-<label> from the BIDS
                        spec (i.e., does not include "ses-"). Specify the
                        session labels as space-separated values after the
                        --session-list option. Default behavior: all of the
                        sessions found under the sub- directory will be
                        combined in the order in which an "ls" on the
                        directory would list them. To have the sessions be
                        combined in a logical order, without providing this
                        this list, the sessions need to be named such that,
                        when listed with "ls", they are listed in the order
                        they should be processed.
  --t1-session-label T1_SESSION_LABEL
                        The session label of the session that contains the T1w
                        data to be used. The session label given here must be
                        one of the sessions being combined.Default behavior:
                        use all T1w data found in all sessions being combined.
  --t2-session-label T2_SESSION_LABEL
                        The session label of the session that contains the T2w
                        data to be used. The session label given here must be
                        one of the sessions being combined.Default behavior:
                        use all T2w data found in all sessions being combined.
  --dataset-name DATASET_NAME
                        Optional alphanumeric name to use when making the
                        output directory. The new directory will be at the
                        same level as the bids_dir passed in, and, by default,
                        will be named "niftis_desc-combined". If this argument
                        is provided its value will replace "combined".
  --owner-group OWNER_GROUP
                        Optional group name or ID, to own new paths and files.
                        Default is None -- i.e., do not change the owner.
```

