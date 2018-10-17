#!/usr/bin/env python
import argparse
import locale
import logging
import os
import psycopg2
import re

from metadata import course_ids, graduation_ids, semester_ids

parser = argparse.ArgumentParser()
parser.add_argument('filename')
parser.add_argument('-d', '--debug', action='store_const', const=logging.DEBUG,
                    default=logging.INFO)
args = parser.parse_args()

logger = logging.getLogger(__name__)
logger.setLevel(args.debug)
ch = logging.StreamHandler()
ch.setLevel(args.debug)
fmt = logging.Formatter('[%(levelname)s - %(filename)s:%(lineno)d] - %(message)s')
ch.setFormatter(fmt)
logger.addHandler(ch)

def parse_file(fp):
    page = 1
    semester_id = None
    grad_id = None
    course_id = None
    class_id = None

    match_semester = re.compile(r'Semestre -\s+(?P<id>\d+)')
    match_graduation = re.compile(r'Curso:\s+(?P<id>\d+)')
    match_class = re.compile(r'\d{5}\w?')

    for line in fp:
        # reset on pagebrk
        if '\f' in line:
            if grad_id is None:
                logger.warning(f'Page {page} couldn\'t be parsed')

            page += 1
            semester_id = None
            grad_id = None
            course_id = None
            class_id = None
            continue

        if 'Semestre -' in line:
            match = match_semester.search(line)
            if not match:
                logger.warning('Semester ID parse error!')
                logger.warning(line)
                continue

            semester_id = match.group('id')
            if semester_id not in semester_ids:
                logger.warning(f'Semester ID not found: {semester_id}')
            continue


        if 'Curso:' in line:
            if semester_id is None:
                logger.warning(f'Found graduation ID before semester on page {page}')
                continue

            match = match_graduation.search(line)
            if not match:
                logger.warning('Graduation ID parse error!')
                logger.warning(line)
                continue

            grad_id = match.group('id')
            if grad_id not in graduation_ids:
                logger.warning(f'Graduation ID not found: {grad_id}')
            continue

        if line[:7] in course_ids:
            course_id = line[:7]
            # logger.info(f'Parsing data for course {course_id}, graduation {grad_id}, semester {semester_id}')

        if not semester_id or not grad_id or not course_id:
            continue

        fields = line.split()

        # on longer tables, page number gets in the middle of some last row.
        # thanks for helping, suckers
        if len(fields) > 10 and fields[-10] == str(page + 13):
            fields.pop(-10)

        # so we double check length...
        if len(fields) < 21:
            continue

        disapproved_attendance = fields[-3]
        class_id, _, total, approved, _, disapproved_grade, _ = fields[-21:-14]

        if total == '0':
            continue

        match = match_class.match(class_id)
        if not match:
            logger.debug(f'Unrecognized class id {class_id}')
            continue

        if int(total) != int(approved) + int(disapproved_grade):
            logger.debug(f'{course_id}@{grad_id} p{page} has inconsistent totals')
            continue

        yield class_id, semester_id, int(grad_id), course_id, int(approved), \
                int(disapproved_grade), int(disapproved_attendance)

user = os.environ.get('POSTGRES_USER')
password = os.environ.get('POSTGRES_PASSWORD')
host = os.environ.get('DATABASE_HOST', 'localhost')
dbname = os.environ.get('POSTGRES_DB')
conn = psycopg2.connect(host=host, user=user, password=password, dbname=dbname)

with open(os.path.abspath(args.filename)) as fp:
    logger.info(f'Parsing {args.filename}...')

    cursor = conn.cursor()
    for class_id, semester_id, graduation_id, course_id, approved, \
            disapproved, attendance in parse_file(fp):
        logger.info(f'Inserting {graduation_id}/{semester_id}/{course_id}/{class_id}')
        cursor.execute("""
            INSERT INTO performances(program_id, class_id, approved, disapproved, attendance)
            SELECT %s, c.id, %s, %s, %s
                FROM classes c
                WHERE c.name = %s AND c.term = %s AND c.course_id = %s
            ON CONFLICT (program_id, class_id) DO UPDATE
                SET approved = excluded.approved,
                    disapproved = excluded.disapproved,
                    attendance = excluded.attendance
        """, (graduation_id, approved, disapproved, attendance, class_id,
              semester_id, course_id))
        conn.commit()
    cursor.close()

conn.close()
