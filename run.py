#!/usr/bin/env python3

__doc__ = \
        """

    Combines data from multiple sessions for one subject so that it can be processed
    as though it were a single session. To do this:

      - Anatomy data will be combined into one directory. The user can specify a session
        where T1w data can be found. Otherwise, all T1w data found in the sessions being
        combined will be used. T1w file will be assigned a run number (in the order
        found) and this run number will replace the session number in the filename.
        Likewise for T2w data.

      - All functional data for the subject will be combined into a single directory by
        copying the data. The task files will be renumbered such that those for the same
        task-<TASKNAME> will have sequential runs. For example, if
        sub-X_ses-Y_task-rest_run-1 through sub-X_ses-Y_task-rest_run-m and
        sub-X_ses-Z_task-rest_run-1 through sub-X_ses-Z_task-rest_run-n are found, then
        sub-X_task-rest_run-1 through sub-X_task-rest_run-(m+n)
        will be written to the func subdirectory of the combined session.
        A metadata field, called SourceFile, in the .json file associated with each file
        written will point back to the original file from which the data was copied.

      - Multiple fmap files can be present, and the 'IntendedFor' field (if any) in the
        metadata for each fmap file will be updated to match the new path in the combined
        session.

        """
__version__ = "0.0.0"


import argparse
import json
import logging
import os
import re
import time
from bids import BIDSLayout
from glob import glob
from shutil import copy, chown

def _cli():
    """
    command line interface
    :return:
    """

    parser = generate_parser()
    args = parser.parse_args()

    kwargs = {
            'bids_dir': args.bids_dir,
            'participant_label': args.participant_label,
            'session_list': args.session_list,
            't1_session_label': args.t1_session_label,
            't2_session_label': args.t2_session_label,
            'dataset_name': args.dataset_name,
            'owner_group': args.owner_group
            }

    interface(**kwargs)


def generate_parser(parser=None):
    """
    Generates the command line parser for this program.
    :return: ArgumentParser for this program.
    """
    if not parser:
        parser = argparse.ArgumentParser(
                description=__doc__,
                formatter_class=argparse.RawDescriptionHelpFormatter
                )
        parser.add_argument(
                'bids_dir',
                help='Full path to the directory with the input BIDS-formatted '
                     'data set. Data must be in BIDS format.'
                )
        parser.add_argument(
                'participant_label',
                help='The label of the participant to be processed. The label '
                     'corresponds to sub-<participant_label> from the BIDS '
                     'specification  (i.e.,does not include "sub-"). '
                )
        parser.add_argument(
                '--session-list',
                dest='session_list',
                metavar="SESSION-LABEL",
                nargs="+",
                help='The labels for the list of sessions to be combined, in the '
                     'order in which their runs should be processed. Each label '
                     'corresponds to ses-<label> from the BIDS spec (i.e., does '
                     'not include "ses-"). Specify the session labels as space-'
                     'separated values after the --session-list option. '
                     'Default behavior: all of the sessions found under the sub- '
                     'directory will be combined in the order in which an "ls" '
                     'on the directory would list them. '
                     'To have the sessions be combined in a logical order, '
                     'without providing this this list, the sessions need to '
                     'be named such that, when listed with "ls", they are '
                     'listed in the order they should be processed. '
                )
        parser.add_argument(
                '--t1-session-label',
                dest='t1_session_label',
                help='The session label of the session that contains the T1w '
                     'data to be used. The session label given here must be one '
                     'of the sessions being combined.'
                     'Default behavior: use all T1w data found in all sessions '
                     'being combined. '
                )
        parser.add_argument(
                '--t2-session-label',
                dest='t2_session_label',
                help='The session label of the session that contains the T2w '
                     'data to be used. The session label given here must be one '
                     'of the sessions being combined.'
                     'Default behavior: use all T2w data found in all sessions '
                     'being combined. '
                )
        parser.add_argument(
                '--dataset-name',
                dest='dataset_name',
                default='combined',
                help='Optional alphanumeric name to use when making the output '
                     'directory. The new directory will be at the same level as '
                     'the bids_dir passed in, and, by default, will be named '
                     '"niftis_desc-combined". If this argument is provided '
                     'its value will replace "combined".'
                )
        parser.add_argument(
                '--owner-group',
                dest='owner_group',
                default=None,
                help='Optional group name or ID, to own new paths and files. '
                     'Default is None -- i.e., do not change the owner. '
                )

        return parser

def make_unisession_files( src_nii, dest_dir, dest_filename, group=None ):
    # Copy both the nii file, and the associated json file.
    # Make sure the new files have the correct group owner.
    # Add the nii's source path into the new .json file.

    dest_nii = os.path.join(dest_dir, dest_filename)
    copy( src_nii, dest_nii )
    logging.info( '%s' % ( src_nii ) )
    logging.info( '  -------> %s' % ( dest_nii ) )

    src_json = re.sub( 'nii.gz', 'json', src_nii )
    dest_json = re.sub( 'nii.gz', 'json', dest_nii )

    # Read the source json.
    json_data = {}
    with open(src_json) as j:
        json_data = json.load(j)

    # Add the SourceFile metadata.
    json_data.update( { 'SourceFile': src_nii } )

    # Write the new json.
    with open(dest_json, mode='w', encoding='UTF-8') as f:
        json.dump( json_data, f, indent=2 )

    logging.info( '%s' % ( src_json ) )
    logging.info( '  -------> %s' % ( dest_json ) )

    if group is not None:
        chown( dest_nii, group=group  )
        chown( dest_json, group=group  )

    return dest_nii, dest_json


def interface( bids_dir, participant_label, session_list=[], t1_session_label=None, t2_session_label=None, dataset_name='combined', owner_group=None ):
    """
    Main application interface.
    :param bids_dir: required, input directory.
    :param participant_label: required, the subject whose sessions are to be combined.
    :param session_list: optional, ordered list of sessions to be combined.
    :param t1_session_label: optional, session that has T1w data to be included.
    :param t2_session_label: optional, session that has T2w data to be included.
    :param dataset_name: optional, name to be used for desc- part of output dir.
    :param owner_group: optional, group owner for new paths and files.
    """
    subject = 'sub-' + participant_label

    # Parameter checking....
    # Make sure the output dir is valid and that we can write to it.
    output_dir = os.path.join(bids_dir, '../niftis_desc-%s' % dataset_name)
    new_subject_dir = os.path.join(output_dir, subject)
    os.makedirs(new_subject_dir, exist_ok=True)
    if owner_group is not None:
        chown( output_dir, group=owner_group  )
        chown( new_subject_dir, group=owner_group  )

    # Log everything used to process the data for this subject.
    log_path = os.path.join( new_subject_dir, 'README' )
    log_format = '%(levelname)s: %(message)s'
    logging.basicConfig( filename=log_path, format=log_format, level=logging.INFO )
    logging.captureWarnings(True)
    logging.info( time.ctime() )
    logging.info( 'Combine Files was run with these values:' )
    logging.info( 'BIDS directory: %s' % bids_dir )
    logging.info( 'Participant label: %s' % participant_label )
    logging.info( 'Session list: %s' %  session_list )
    logging.info( 'T1w session label: %s' % t1_session_label )
    logging.info( 'T2w session label: %s' % t2_session_label )
    logging.info( 'Dataset name: %s' % dataset_name )
    logging.info( 'Owner group: %s' % owner_group )

    new_anat_dir = os.path.join(new_subject_dir, 'anat')
    os.makedirs(new_anat_dir, exist_ok=True)
    if owner_group is not None:
        chown( new_anat_dir, group=owner_group  )

    # Make sure we can get to the input we need.
    # Get the bids layout.
    assert os.path.isdir(bids_dir), '%s is not a directory!' % bids_dir
    layout = BIDSLayout(bids_dir, absolute_paths=True)
    assert layout is not None, 'Unable to get bids layout from directory!' % bids_dir

    # Get the list of subjects.
    all_subjects = layout.get_subjects()
    assert participant_label in all_subjects, 'subject %s is not in the BIDS layout of directory %s.' % (participant_label, bids_dir)

    # Get the list of all of the sessions.
    all_sessions = layout.get_sessions(subject=participant_label)

    # Filter by the sessions we are supposed to use, keeping the order.
    if session_list and session_list is not None and isinstance(session_list, list) and  len(session_list) > 0:
        for session in session_list:
            assert session in all_sessions, 'subject %s does not have session %s' % (subject, session)
    else:
        # Use all of the sessions found in the BIDS layout for the subject,
        # ordered by name.
        session_list = sorted(all_sessions)

    # Get the list of all of the tasks found in the sessions being combined.
    task_list = layout.get_tasks(subject=participant_label, session=session_list)

    # Get the T1w and T2w data from the appropriate session(s).
    t1w_sessions=[]
    if t1_session_label is None:
        # Use all of the sessions being combined when we get the T1w data.
        t1w_sessions.extend(session_list)
    else:
        # Get data only from the session specified.
        assert t1_session_label in session_list, 'session for T1ws (%s) is not in the list of sessions to be combined' % t1_session_label
        t1w_sessions.append(t1_session_label)

    t2w_sessions=[]
    if t2_session_label is None:
        # Use all of the sessions being combined when we get the T2w data.
        t2w_sessions.extend(session_list)
    else:
        # Get data only from the session specified.
        assert t2_session_label in session_list, 'session for T2ws (%s) is not in the list of sessions to be combined' % t2_session_label
        t2w_sessions.append(t2_session_label)

    t1ws=[]
    t2ws=[]
    all_fmaps=[]
    funcs={}
    for task in task_list:
        funcs[task] = []

    # Visit each session being combined, in the order specified, to get files.
    for session in session_list:
        if session in t1w_sessions:
            t1ws_subset = layout.get(subject=participant_label, session=session, datatype='anat', suffix='T1w', extension='nii.gz')
            t1ws.extend(t1ws_subset)
        if session in t2w_sessions:
            t2ws_subset = layout.get(subject=participant_label, session=session, datatype='anat', suffix='T2w', extension='nii.gz')
            t2ws.extend(t2ws_subset)

        # Get all fmaps.
        all_fmaps.extend(layout.get(subject=participant_label, session=session, datatype='fmap', extension='.nii.gz'))

        # Get list of funcs for each task.
        for task in task_list:
            funcs_subset = layout.get(subject=participant_label, session=session, task=task, datatype='func', extension='.nii.gz')
            funcs[task].extend(funcs_subset)

    assert len(t1ws) > 0, 'No T1w data were found for %s in session(s) %s ' % (subject, t1w_sessions)
    assert len(t2ws) > 0, 'No T2w data were found for %s in session(s) %s ' % (subject, t2w_sessions)

    if len(funcs) == 0:
        logging.warning("Subject %s has only anatomical data." % subject)

    if len(all_fmaps) == 0:
        logging.warning('No fmap data were found for subject %s.' % subject)

    # Have what we need, ready to go!
    width = 2
    run = 1
    for t in t1ws:
        run_str = '_run-' + str(run).zfill(width)
        new_filename = re.sub(r'_ses-[^_]+', run_str, t.filename)
        make_unisession_files( t.path, new_anat_dir, new_filename, group=owner_group )
        run += 1

    run = 1
    for t in t2ws:
        run_str = '_run-' + str(run).zfill(width)
        new_filename = re.sub(r'_ses-[^_]+', run_str, t.filename)
        make_unisession_files( t.path, new_anat_dir, new_filename, group=owner_group )
        run += 1

    if len(funcs) > 0:
        new_func_dir = os.path.join(new_subject_dir, 'func')
        os.makedirs(new_func_dir, exist_ok=True)

    for task in task_list:
        num_tasks = len(funcs[task])
        # Check for *more* than 99 runs of the task!
        if num_tasks > 100:
            width = 3
        else:
            width = 2

        # Renumber all of the tasks, preserving the order.
        run = 1
        for f in funcs[task]:

            run_str = '_run-' + str(run).zfill(width)
            run += 1

            new_filename = re.sub( r'_ses-[^_]+', '', f.filename )
            if '_run-' in new_filename:
                new_filename = re.sub( r'_run-[\d]+', run_str, new_filename )
            else:
                # If there is only one run of a task, BIDS does not *require* the
                # '_run-' part of the filename. To keep things consistent throughout
                # our pipelines, add the '_run-' to the new filename.
                new_filename = re.sub( r'task-[^_]+', 'task-' + task + run_str, new_filename )

            make_unisession_files( f.path, new_func_dir, new_filename, group=owner_group )

    width = 2


    if len(all_fmaps) > 0:
        new_fmap_dir = os.path.join(new_subject_dir, 'fmap')
        os.makedirs(new_fmap_dir, exist_ok=True)

        gen_fmaps=[]
        aps=[]
        pas=[]

        for f in all_fmaps:
            direct = f.get_entities().get('dir', 'NODIR').upper()
            if direct == 'PA':
                pas.append(f)
                run_str = '_run-' + str(len(pas)).zfill(width)

            elif direct == 'AP':
                aps.append(f)
                run_str = '_run-' + str(len(aps)).zfill(width)

            elif direct == 'NODIR':
                gen_fmaps.append(f)
                run_str = '_run-' + str(len(gen_fmaps)).zfill(width)

            else:
                logging.warning('Direction \"%s\" was not recognized.' % direct)
                gen_fmaps.append(f)
                run_str = '_run-' + str(len(gen_fmaps)).zfill(width)

            # Replace the session part of the string with a run number so names will
            # still be unique.
            new_filename = re.sub(r'_ses-[^_]+', run_str, f.filename)
            make_unisession_files( f.path, new_fmap_dir, new_filename, group=owner_group )

    # TODO: edit IntendedFor field of each new fmap json: fix dir (new_anat or new_func) and fname!


if __name__ == '__main__':
    _cli()

