from pathlib import Path
import sqlite3
import argparse
import glob
import logging
import sys

import psd_tools
from psd_tools import PSDImage
from PIL import Image
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.pyplot import imshow


def get_logger():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    output_file_handler = logging.FileHandler("output.log")
    stdout_handler = logging.StreamHandler(sys.stdout)

    logger.addHandler(output_file_handler)
    logger.addHandler(stdout_handler)

    return logger


def show_layer(layer):
    img = layer.composite()
    plt.figure()
    plt.imshow(img)
    return layer


def save_layer_img(layers_dir, layer, layer_order, show=False):
    img = layer.composite()
    if show == True:
        plt.figure()
        plt.imshow(img)
    layer_path = layers_dir / Path(str(layer_order) + '.png')
    # Convert CMYK to RGB
    img.convert('RGB').save(layer_path)
    return layer_path


def create_table(c):
    c.execute('''CREATE TABLE creatives
                 (creative_id integer primary key autoincrement,
                  psd_stem text unique,
                  psd_path text unique)'''
    )
    logger.info('Created Table "creatives"')

    c.execute('''CREATE TABLE layers
                 (layer_id integer primary key autoincrement,
                  psd_stem text,
                  psd_path text,
                  layer_path text,
                  layer_order int,
                  left int,
                  top int,
                  right int,
                  bottom int,
                  foreign key (psd_path) references creatives (psd_path))'''
    )
    logger.info('Created Table "layers"')
    return


def get_args():
    parser = argparse.ArgumentParser(description='Decompose psd files into layers, recording information into sqlite.')
    parser.add_argument('--input-dir', type=str, help='example: /srv/datasets/septeni/psd/YDN/', required=True)
    parser.add_argument('--output-dir', type=str, help='example: /srv/datasets/septeni/decomposed_psd/YDN/', required=True)
    parser.add_argument('--create-table', type=bool, action='store_true', help='Create Table', required=True)

    return parser.parse_args()


def main():
    args = get_args()

    # TODO: Use argparse
    input_dir = args.input_dir
    logger.info('Input directory: {}'.format(input_dir))
    output_dir = args.output_dir
    logger.info('Input directory: {}'.format(output_dir))

    # Initialize sqlite
    db_path = 'decomposed_psd.db'
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    if args.create_table:
        create_table(c)

    psd_paths = glob.glob(str(Path(input_dir) / Path('*.psd')))

    psd_paths_len = len(psd_paths)
    logger.info('All files: {}'.format(psd_paths_len))

    for psd_idx, psd_path in enumerate(psd_paths):
        logger.info(' - [{:6}/{:6}] {}'.format(psd_idx, psd_paths_len, psd_path))

        psd_stem = Path(psd_path).stem
        c.execute("INSERT INTO creatives (psd_stem, psd_path) VALUES ('{}', '{}')".format(psd_stem, psd_path))

        # XXX: Test run
        try:
            psd = PSDImage.open(psd_path)

            # Create a directory to save layers image
            layers_dir = Path(output_dir) / Path(psd_stem)
            layers_dir.mkdir(parents=True, exist_ok=True)

            layers_len = len(psd)
            for layer_idx, layer in enumerate(psd):
                logger.info('    - [{:3}/{:3}] {}'.format(layer_idx, layers_len, layer.name))

                layer_path = save_layer_img(layers_dir, layer, layer_idx)

                left, top, right, bottom = layer.bbox
                c.execute(("INSERT INTO layers (psd_stem, psd_path, layer_path, layer_order, left, top, right, bottom) "
                           "values ('{}', '{}', '{}', {}, {}, {}, {}, {})"
                           ).format(psd_stem, psd_path, layer_path, layer_idx, left, top, right, bottom
                ))
            conn.commit()
        except Exception as e:
            logger.error('\n***** ERROR: {} *****\n'.format(psd_path))
            logger.error(e)
    conn.close()
    return


if __name__ == '__main__':
    logger = get_logger()
    main()

